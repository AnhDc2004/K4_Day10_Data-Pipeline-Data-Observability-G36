from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "src"))

from core.config import load_settings
from core.utils import read_json
from evaluation.testset import validate_test_set, verify_test_set_against_index
from retrieval.agent import build_agent
from retrieval.contract import validate_clean_dataframe
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    return value


def _run_retrieval_checks(index: LocalEmbeddingIndex, test_set: list[dict[str, Any]]) -> dict[str, Any]:
    first_item = test_set[0]
    first_paper_id = first_item["ground_truth_doc_ids"][0]
    first_title = first_item["question"].split("'")[1]

    semantic_results = index.search("agentic retrieval augmented generation", top_k=4)
    id_lookup = index.lookup(first_paper_id)
    title_lookup = index.lookup(first_title)
    qa_results = [answer_question(item["question"], settings=index.settings, index=index) for item in test_set[:4]]

    return {
        "semantic_search": {
            "query": "agentic retrieval augmented generation",
            "count": len(semantic_results),
            "top_results": [
                {"paper_id": result.paper_id, "title": result.title, "score": result.score}
                for result in semantic_results
            ],
            "success": bool(semantic_results),
        },
        "exact_lookup_by_paper_id": {
            "value": first_paper_id,
            "title": id_lookup["title"] if id_lookup else None,
            "success": id_lookup is not None,
        },
        "exact_lookup_by_title": {
            "value": first_title,
            "paper_id": title_lookup["paper_id"] if title_lookup else None,
            "success": title_lookup is not None,
        },
        "qa_samples": [
            {
                "id": item["id"],
                "retrieved_doc_ids": result.retrieved_doc_ids,
                "answer": result.answer,
                "success": bool(result.retrieved_doc_ids),
            }
            for item, result in zip(test_set[:4], qa_results, strict=True)
        ],
    }


def _run_agent_smoke(agent: Any, question: str) -> tuple[str, int]:
    """Invoke the agent and require at least one tool message in the trace."""
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    messages = result.get("messages", [])
    tool_messages = [
        message
        for message in messages
        if getattr(message, "type", "") == "tool" or message.__class__.__name__ == "ToolMessage"
    ]
    if not messages:
        return "", 0
    final_message = messages[-1]
    content = getattr(final_message, "content", str(final_message))
    if isinstance(content, list):
        content = " ".join(str(item) for item in content)
    return str(content), len(tool_messages)


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    config = payload["index"]
    retrieval = payload["retrieval"]
    test_contract = payload["test_set"]["contract"]
    index_contract = payload["test_set"]["index_lookup"]
    agent = payload["agent"]
    lines = [
        "# Vai trò 4 — CP2 RAG & Agent",
        "",
        f"- Overall status: **{payload['status'].upper()}**",
        f"- Clean rows indexed: **{config['documents']}**",
        f"- Test set samples: **{payload['test_set']['samples']}**",
        "",
        "## Baseline index",
        "",
        f"- Collection: `{config['collection_name']}`",
        f"- Manifest: `{config['manifest']}`",
        f"- Embedding model: `{config['embedding_model']}`",
        f"- Backend: `{config['backend']}`",
        f"- Persist path: `{config['persist_path']}`",
        "",
        "## Test-set handoff",
        "",
        f"- Test-set contract valid: **{test_contract['valid']}**",
        f"- Missing document IDs: `{index_contract['missing_doc_ids']}`",
        f"- Missing titles: `{index_contract['missing_titles']}`",
        "",
        "## Retrieval smoke tests",
        "",
        f"- Semantic search: **{retrieval['semantic_search']['success']}** ({retrieval['semantic_search']['count']} results)",
        f"- Exact lookup by paper ID: **{retrieval['exact_lookup_by_paper_id']['success']}**",
        f"- Exact lookup by title: **{retrieval['exact_lookup_by_title']['success']}**",
        f"- QA samples with retrieved documents: **{sum(item['success'] for item in retrieval['qa_samples'])}/{len(retrieval['qa_samples'])}**",
        "",
        "## Agent smoke test",
        "",
        f"- Provider/model: `{agent['provider']}` / `{agent['model']}`",
        f"- Status: **{agent['status']}**",
        f"- Tool evidence: `{agent['tool_evidence']}`",
        f"- Answer preview: {agent['answer_preview']}",
        "",
        "## Scope guard",
        "",
        "- Chỉ tạo baseline collection và manifest.",
        "- Chưa tạo corrupted/repaired artifact.",
        "- Chưa chạy evaluator đầy đủ hoặc phase1 pipeline.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    settings = load_settings(PROJECT_DIR)
    clean_df = pd.read_csv(settings.paths.clean_csv)
    clean_contract = validate_clean_dataframe(clean_df)
    if clean_contract["status"] != "pass":
        raise RuntimeError(f"Clean contract failed: {clean_contract['hard_failures']}")

    index = LocalEmbeddingIndex.build(
        clean_df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    manifest = read_json(settings.paths.embeddings_json)
    test_set = read_json(settings.paths.eval_testset)
    if not isinstance(test_set, list):
        raise ValueError(f"Expected a JSON list in {settings.paths.eval_testset}")

    test_errors = validate_test_set(test_set, clean_df)
    index_lookup = verify_test_set_against_index(test_set, index)
    retrieval = _run_retrieval_checks(index, test_set)

    agent_result: dict[str, Any] = {
        "provider": settings.llm_provider,
        "model": settings.model_name,
        "status": "fail",
        "tool_evidence": "unverified",
        "answer_preview": "",
    }
    try:
        agent = build_agent(settings, index)
        question = test_set[0]["question"]
        answer, tool_message_count = _run_agent_smoke(agent, question)
        agent_result.update(
            {
                "status": "pass" if answer.strip() and tool_message_count > 0 else "fail",
                "tool_evidence": f"{tool_message_count} tool message(s) in agent trace",
                "answer_preview": answer[:300].replace("\n", " "),
            }
        )
    except Exception as exc:
        agent_result["error"] = str(exc)

    payload = {
        "status": "pass" if not test_errors and index_lookup["success"] and all(
            item["success"] for item in retrieval["qa_samples"]
        ) and agent_result["status"] == "pass" else "fail",
        "index": {
            "backend": manifest["backend"],
            "embedding_model": manifest["embedding_model"],
            "persist_path": manifest["persist_path"],
            "collection_name": manifest["collection_name"],
            "manifest": str(settings.paths.embeddings_json),
            "documents": len(manifest["documents"]),
        },
        "test_set": {
            "samples": len(test_set),
            "contract": {"valid": not test_errors, "errors": test_errors},
            "index_lookup": index_lookup,
        },
        "retrieval": retrieval,
        "agent": agent_result,
    }
    report_path = PROJECT_DIR / "report" / "role4_cp2.md"
    _write_report(report_path, _json_safe(payload))
    print(f"CP2 report: {report_path}")
    print(f"Baseline collection: {index.collection_name}; documents: {len(index.documents)}")
    print(f"Agent smoke test: {agent_result['status']}")
    if payload["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
