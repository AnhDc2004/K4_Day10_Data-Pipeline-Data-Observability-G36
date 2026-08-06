from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "src"))

from core.config import load_settings
from core.utils import read_json
from evaluation.testset import verify_test_set_against_index
from observability.quality import audit_index_manifest
from retrieval.agent import build_agent
from retrieval.index import LocalEmbeddingIndex


def _agent_smoke(agent: Any, question: str) -> dict[str, Any]:
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    messages = result.get("messages", [])
    tool_messages = [
        message
        for message in messages
        if getattr(message, "type", "") == "tool" or message.__class__.__name__ == "ToolMessage"
    ]
    answer = getattr(messages[-1], "content", "") if messages else ""
    if isinstance(answer, list):
        answer = " ".join(str(item) for item in answer)
    return {
        "answer": str(answer),
        "tool_messages": len(tool_messages),
        "success": bool(str(answer).strip()) and bool(tool_messages),
    }


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    retrieval = payload["retrieval"]
    artifacts = payload["artifacts"]
    lines = [
        "# Vai trò 4 — CP3 Baseline Verification",
        "",
        f"- Overall status: **{payload['status'].upper()}**",
        "- Index không được rebuild trong CP3.",
        "- Corrupted/repaired flow chưa chạy.",
        "",
        "## Artifact checks",
        "",
        f"- Manifest tồn tại: **{artifacts['manifest']}**",
        f"- Baseline metrics tồn tại: **{artifacts['baseline_metrics']}**",
        f"- Baseline answers tồn tại: **{artifacts['baseline_answers']}**",
        f"- Quality/freshness tồn tại: **{artifacts['quality_freshness']}**",
        f"- Phase1 report tồn tại: **{artifacts['phase1_report']}**",
        "",
        "## Index and handoff",
        "",
        f"- Collection: `{payload['collection']}`",
        f"- Documents loaded: **{payload['documents']}**",
        f"- Manifest audit: **{payload['audit_success']}**",
        f"- Test-set verification: **{payload['test_set_success']}**",
        f"- Missing document IDs: `{payload['missing_doc_ids']}`",
        f"- Missing titles: `{payload['missing_titles']}`",
        "",
        "## Retrieval evidence",
        "",
        f"- Semantic search: **{retrieval['semantic_success']}** ({retrieval['semantic_count']} results)",
        f"- Exact lookup by paper ID: **{retrieval['id_lookup_success']}**",
        f"- Exact lookup by title: **{retrieval['title_lookup_success']}**",
        f"- Agent answer: **{retrieval['agent_success']}**",
        f"- Agent tool messages: **{retrieval['agent_tool_messages']}**",
        f"- Baseline answer hits: **{retrieval['answer_hits']}/{retrieval['answer_count']}**",
        f"- Baseline answer misses: **{retrieval['answer_misses']}**",
        "",
        "## Evidence limitation",
        "",
        "Baseline hiện có 24/24 retrieval hits, nên không có miss thật trong `baseline_answers.json` để trình bày. Không tự tạo hoặc gắn nhãn miss giả.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    settings = load_settings(PROJECT_DIR)
    clean_df = pd.read_csv(settings.paths.clean_csv)
    manifest = read_json(settings.paths.embeddings_json)
    test_set = read_json(settings.paths.eval_testset)
    metrics = read_json(settings.paths.baseline_metrics)
    answers = read_json(settings.paths.baseline_answers)

    index = LocalEmbeddingIndex.load(settings, settings.paths.embeddings_json)
    audit = audit_index_manifest(settings, settings.paths.embeddings_json, clean_df)
    test_set_verification = verify_test_set_against_index(test_set, index)

    semantic_results = index.search("agentic retrieval augmented generation", top_k=settings.top_k)
    first_item = test_set[0]
    first_id = first_item["ground_truth_doc_ids"][0]
    first_title = first_item["question"].split("'")[1]
    id_lookup = index.lookup(first_id)
    title_lookup = index.lookup(first_title)

    agent_result = _agent_smoke(build_agent(settings, index), first_item["question"])
    answer_hits = sum(1 for answer in answers if answer.get("retrieval_hit") is True)
    artifacts = {
        "manifest": settings.paths.embeddings_json.exists(),
        "baseline_metrics": settings.paths.baseline_metrics.exists(),
        "baseline_answers": settings.paths.baseline_answers.exists(),
        "quality_freshness": settings.paths.quality_dir.joinpath("baseline_quality.json").exists()
        and settings.paths.freshness_report.exists(),
        "phase1_report": settings.paths.baseline_report.exists(),
    }
    retrieval = {
        "semantic_success": bool(semantic_results),
        "semantic_count": len(semantic_results),
        "id_lookup_success": id_lookup is not None,
        "title_lookup_success": title_lookup is not None,
        "agent_success": agent_result["success"],
        "agent_tool_messages": agent_result["tool_messages"],
        "answer_hits": answer_hits,
        "answer_count": len(answers),
        "answer_misses": len(answers) - answer_hits,
    }
    status = all(artifacts.values()) and audit["success"] and test_set_verification["success"] and all(
        [
            retrieval["semantic_success"],
            retrieval["id_lookup_success"],
            retrieval["title_lookup_success"],
            retrieval["agent_success"],
            metrics.get("samples") == len(test_set),
        ]
    )
    payload = {
        "status": "pass" if status else "blocked",
        "collection": manifest.get("collection_name"),
        "documents": len(index.documents),
        "audit_success": audit["success"],
        "test_set_success": test_set_verification["success"],
        "missing_doc_ids": test_set_verification["missing_doc_ids"],
        "missing_titles": test_set_verification["missing_titles"],
        "artifacts": artifacts,
        "retrieval": retrieval,
    }
    report_path = PROJECT_DIR / "report" / "role4_cp3.md"
    _write_report(report_path, payload)
    print(f"CP3 report: {report_path}")
    print(f"audit={audit['success']} test_set={test_set_verification['success']} agent={agent_result['success']}")
    print(f"hits={answer_hits}/{len(answers)} misses={len(answers) - answer_hits}")
    if not status:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

