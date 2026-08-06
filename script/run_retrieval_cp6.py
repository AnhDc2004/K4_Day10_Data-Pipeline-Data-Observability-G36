from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "src"))

from core.config import load_settings
from core.utils import read_json, write_text
from evaluation.testset import verify_test_set_against_index
from observability.quality import audit_index_manifest
from retrieval.agent import build_agent
from retrieval.contract import validate_clean_dataframe
from retrieval.index import LocalEmbeddingIndex


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _provider_error(exc: Exception) -> str:
    """Keep provider failures actionable without serializing URLs or credentials."""
    message = str(exc)
    if "Error code: 403" in message:
        return "Provider request rejected (HTTP 403); check OpenRouter quota and key limits."
    return f"{type(exc).__name__}: provider request failed."


def _agent_smoke(settings, index: LocalEmbeddingIndex, question: str) -> dict[str, Any]:
    try:
        messages = build_agent(settings, index).invoke(
            {"messages": [{"role": "user", "content": question}]}
        ).get("messages", [])
    except Exception as exc:
        return {"success": False, "tool_messages": 0, "answer": "", "error": _provider_error(exc)}

    tool_messages = [
        message
        for message in messages
        if getattr(message, "type", "") == "tool" or message.__class__.__name__ == "ToolMessage"
    ]
    answer = getattr(messages[-1], "content", "") if messages else ""
    if isinstance(answer, list):
        answer = " ".join(str(item) for item in answer)
    return {
        "success": bool(str(answer).strip()) and bool(tool_messages),
        "tool_messages": len(tool_messages),
        "answer": str(answer),
        "error": "",
    }


def _summarize(results: list) -> list[dict[str, object]]:
    return [
        {"paper_id": result.paper_id, "title": result.title, "score": round(result.score, 4)}
        for result in results
    ]


def main() -> None:
    settings = load_settings(PROJECT_DIR)
    paths = settings.paths
    required = {
        "baseline_manifest": paths.embeddings_json,
        "corrupted_manifest": paths.corrupted_embeddings_json,
        "repaired_clean": paths.repaired_clean_json,
        "repair_validation": paths.repaired_metrics.parent / "repair_validation.json",
        "test_set": paths.eval_testset,
    }
    missing = [name for name, path in required.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing CP6 handoff artifacts: {missing}")

    repaired_df = pd.DataFrame(read_json(paths.repaired_clean_json))
    repair_validation = read_json(required["repair_validation"])
    if not repair_validation.get("success"):
        raise RuntimeError("Repair validation is not successful; repaired index must not be built.")

    repaired_contract = validate_clean_dataframe(repaired_df)
    if repaired_contract["status"] != "pass":
        raise RuntimeError(f"Repaired retrieval contract failed: {repaired_contract}")

    baseline_manifest_hash = _sha256(paths.embeddings_json)
    corrupted_manifest_hash = _sha256(paths.corrupted_embeddings_json)
    baseline_index = LocalEmbeddingIndex.load(settings, paths.embeddings_json)
    corrupted_index = LocalEmbeddingIndex.load(settings, paths.corrupted_embeddings_json)
    baseline_count = baseline_index.collection.count()
    corrupted_count = corrupted_index.collection.count()

    repaired_index = LocalEmbeddingIndex.build(
        df=repaired_df,
        settings=settings,
        embeddings_output_path=paths.repaired_embeddings_json,
    )
    repaired_manifest_audit = audit_index_manifest(settings, paths.repaired_embeddings_json, repaired_df)
    test_set = read_json(paths.eval_testset)
    test_set_check = verify_test_set_against_index(test_set, repaired_index)

    first_test = test_set[0]
    paper_id = first_test["ground_truth_doc_ids"][0]
    title = first_test["question"].split("'")[1]
    semantic_query = "agentic retrieval augmented generation"
    semantic_results = repaired_index.search(semantic_query, top_k=settings.top_k)
    if os.getenv("CP6_SKIP_AGENT", "").lower() in {"1", "true", "yes"}:
        agent_result = {
            "success": False,
            "tool_messages": 0,
            "answer": "",
            "error": "Skipped by CP6_SKIP_AGENT; provider smoke must be run separately.",
        }
    else:
        agent_result = _agent_smoke(settings, repaired_index, first_test["question"])

    baseline_unchanged = (
        _sha256(paths.embeddings_json) == baseline_manifest_hash
        and LocalEmbeddingIndex.load(settings, paths.embeddings_json).collection.count() == baseline_count
    )
    corrupted_unchanged = (
        _sha256(paths.corrupted_embeddings_json) == corrupted_manifest_hash
        and LocalEmbeddingIndex.load(settings, paths.corrupted_embeddings_json).collection.count() == corrupted_count
    )

    evidence = {
        "collections": {
            "baseline": {"name": baseline_index.collection_name, "documents": baseline_count},
            "corrupted": {"name": corrupted_index.collection_name, "documents": corrupted_count},
            "repaired": {"name": repaired_index.collection_name, "documents": repaired_index.collection.count()},
        },
        "repaired_contract": repaired_contract,
        "repaired_manifest_audit": repaired_manifest_audit,
        "test_set": test_set_check,
        "semantic_query": semantic_query,
        "semantic_results": _summarize(semantic_results),
        "lookup_by_id": repaired_index.lookup(paper_id) is not None,
        "lookup_by_title": repaired_index.lookup(title) is not None,
        "agent": agent_result,
        "baseline_unchanged": baseline_unchanged,
        "corrupted_unchanged": corrupted_unchanged,
    }
    status = all(
        [
            repaired_index.collection_name == settings.repaired_collection_name,
            repaired_index.collection.count() == len(repaired_df),
            repaired_manifest_audit["success"],
            test_set_check["success"],
            bool(semantic_results),
            evidence["lookup_by_id"],
            evidence["lookup_by_title"],
            agent_result["success"],
            baseline_unchanged,
            corrupted_unchanged,
        ]
    )

    report = [
        "# Vai trò 4 — CP6 Repaired Retrieval & Agent",
        "",
        f"- Overall status: **{'PASS' if status else 'BLOCKED'}**",
        "- Repaired data được bàn giao từ raw-based repair và không được sửa trong script này.",
        "",
        "## Collection isolation",
        f"- Baseline: `{baseline_index.collection_name}` ({baseline_count} documents)",
        f"- Corrupted: `{corrupted_index.collection_name}` ({corrupted_count} documents)",
        f"- Repaired: `{repaired_index.collection_name}` ({repaired_index.collection.count()} documents)",
        f"- Baseline unchanged: **{baseline_unchanged}**",
        f"- Corrupted unchanged: **{corrupted_unchanged}**",
        "",
        "## Repaired verification",
        f"- Retrieval contract: **{repaired_contract['status'] == 'pass'}**",
        f"- Manifest audit: **{repaired_manifest_audit['success']}**",
        f"- Test-set verification: **{test_set_check['success']}**",
        f"- Missing document IDs: `{test_set_check['missing_doc_ids']}`",
        f"- Missing titles: `{test_set_check['missing_titles']}`",
        "",
        "## Retrieval and agent evidence",
        f"- Semantic search `{semantic_query}`: **{len(semantic_results)}** results",
        f"- Exact lookup by paper ID: **{evidence['lookup_by_id']}**",
        f"- Exact lookup by title: **{evidence['lookup_by_title']}**",
        f"- Agent tool messages: **{agent_result['tool_messages']}**",
        f"- Agent answer present: **{bool(agent_result['answer'].strip())}**",
        f"- Agent error: `{agent_result['error']}`",
        "",
        "## Scope limitation",
        "Repaired metrics/answers and the three-state comparison report remain evaluator/Lead artifacts. "
        "This report proves the repaired retrieval and agent handoff only.",
        "",
    ]
    report_path = PROJECT_DIR / "report" / "role4_cp6.md"
    write_text(report_path, "\n".join(report))
    print(json.dumps({"status": "PASS" if status else "BLOCKED", "report": str(report_path), "evidence": evidence}, ensure_ascii=True))
    if not status:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
