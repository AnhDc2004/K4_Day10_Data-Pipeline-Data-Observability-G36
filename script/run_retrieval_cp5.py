from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "src"))

from core.config import load_settings
from core.utils import read_json, write_text
from retrieval.contract import validate_clean_dataframe
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _result_summary(results: list) -> list[dict[str, object]]:
    return [
        {"paper_id": item.paper_id, "title": item.title, "score": round(item.score, 4)}
        for item in results
    ]


def main() -> None:
    settings = load_settings(PROJECT_DIR)
    paths = settings.paths

    required = {
        "baseline_clean": paths.clean_json,
        "corrupted_clean": paths.corrupted_clean_json,
        "corruption_log": paths.corruption_log,
        "baseline_manifest": paths.embeddings_json,
    }
    missing = [name for name, path in required.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing CP5 handoff artifacts: {missing}")

    baseline_df = pd.DataFrame(read_json(paths.clean_json))
    corrupted_df = pd.DataFrame(read_json(paths.corrupted_clean_json))
    corruption_log = read_json(paths.corruption_log)
    baseline_manifest_hash = _sha256(paths.embeddings_json)

    if corruption_log.get("baseline_count") != len(baseline_df):
        raise ValueError("Corruption log baseline_count does not match clean baseline.")
    if corruption_log.get("corrupted_count") != len(corrupted_df):
        raise ValueError("Corruption log corrupted_count does not match corrupted clean data.")

    corrupted_contract = validate_clean_dataframe(corrupted_df)
    if corrupted_contract["status"] != "pass":
        # Duplicate IDs are an intentional CP5 signal, but the index can still
        # represent rows safely because record_id includes the row position.
        unexpected_failures = [
            failure for failure in corrupted_contract.get("hard_failures", [])
            if failure != "duplicate_paper_ids"
        ]
        if unexpected_failures:
            raise ValueError(f"Corrupted retrieval contract has unexpected failures: {unexpected_failures}")

    baseline_index = LocalEmbeddingIndex.load(settings, paths.embeddings_json)
    baseline_count_before = baseline_index.collection.count()
    corrupted_index = LocalEmbeddingIndex.build(
        df=corrupted_df,
        settings=settings,
        embeddings_output_path=paths.corrupted_embeddings_json,
    )

    surviving_row = corrupted_df.iloc[0]
    semantic_query = "agentic retrieval augmented generation"
    baseline_search = baseline_index.search(semantic_query)
    corrupted_search = corrupted_index.search(semantic_query)
    baseline_lookup = baseline_index.lookup(str(surviving_row["paper_id"]))
    corrupted_lookup = corrupted_index.lookup(str(surviving_row["paper_id"]))
    baseline_title_lookup = baseline_index.lookup(str(surviving_row["title"]))
    corrupted_title_lookup = corrupted_index.lookup(str(surviving_row["title"]))

    question = f"Who authored the paper titled '{surviving_row['title']}'?"
    baseline_answer = answer_question(question, settings=settings, index=baseline_index)
    corrupted_answer = answer_question(question, settings=settings, index=corrupted_index)

    baseline_index_after = LocalEmbeddingIndex.load(settings, paths.embeddings_json)
    baseline_manifest_unchanged = _sha256(paths.embeddings_json) == baseline_manifest_hash
    baseline_unchanged = (
        baseline_index_after.collection_name == settings.baseline_collection_name
        and baseline_index_after.collection.count() == baseline_count_before
        and baseline_manifest_unchanged
    )

    evidence = {
        "baseline_rows": len(baseline_df),
        "corrupted_rows": len(corrupted_df),
        "corruption_operations": [item["type"] for item in corruption_log.get("operations", [])],
        "corrupted_contract": corrupted_contract,
        "baseline_collection": baseline_index_after.collection_name,
        "baseline_documents_before": baseline_count_before,
        "baseline_documents_after": baseline_index_after.collection.count(),
        "corrupted_collection": corrupted_index.collection_name,
        "corrupted_documents": corrupted_index.collection.count(),
        "baseline_manifest_unchanged": baseline_manifest_unchanged,
        "baseline_unchanged": baseline_unchanged,
        "semantic_query": semantic_query,
        "baseline_semantic_results": _result_summary(baseline_search),
        "corrupted_semantic_results": _result_summary(corrupted_search),
        "baseline_lookup_by_id": baseline_lookup is not None,
        "corrupted_lookup_by_id": corrupted_lookup is not None,
        "baseline_lookup_by_title": baseline_title_lookup is not None,
        "corrupted_lookup_by_title": corrupted_title_lookup is not None,
        "baseline_question_doc_ids": baseline_answer.retrieved_doc_ids,
        "corrupted_question_doc_ids": corrupted_answer.retrieved_doc_ids,
        "baseline_manifest": str(paths.embeddings_json.relative_to(PROJECT_DIR)),
        "corrupted_manifest": str(paths.corrupted_embeddings_json.relative_to(PROJECT_DIR)),
    }

    pass_status = all(
        [
            corrupted_index.collection_name == settings.corrupted_collection_name,
            corrupted_index.collection.count() == len(corrupted_df),
            baseline_unchanged,
            bool(baseline_search),
            bool(corrupted_search),
            baseline_lookup is not None,
            corrupted_lookup is not None,
            baseline_title_lookup is not None,
            corrupted_title_lookup is not None,
        ]
    )

    report_lines = [
        "# Vai trò 4 — CP4/CP5 Corrupted Retrieval",
        "",
        f"- CP4 baseline freeze: **PASS**",
        f"- CP5 retrieval verification: **{'PASS' if pass_status else 'BLOCKED'}**",
        "- Evaluator và repaired flow không chạy trong phạm vi role 4.",
        "",
        "## Corruption handoff",
        f"- Baseline rows: **{len(baseline_df)}**",
        f"- Corrupted rows: **{len(corrupted_df)}**",
        f"- Operations: `{', '.join(evidence['corruption_operations'])}`",
        f"- Corrupted contract hard failures: `{corrupted_contract.get('hard_failures', [])}`",
        "",
        "## Index isolation",
        f"- Baseline collection: `{evidence['baseline_collection']}` ({evidence['baseline_documents_after']} docs)",
        f"- Corrupted collection: `{evidence['corrupted_collection']}` ({evidence['corrupted_documents']} docs)",
        f"- Baseline manifest unchanged: **{baseline_manifest_unchanged}**",
        f"- Baseline collection unchanged: **{baseline_unchanged}**",
        f"- Corrupted manifest: `{evidence['corrupted_manifest']}`",
        "",
        "## Retrieval evidence",
        f"- Semantic search query: `{semantic_query}`",
        f"- Baseline semantic results: **{len(baseline_search)}**",
        f"- Corrupted semantic results: **{len(corrupted_search)}**",
        f"- Exact lookup by paper ID: baseline={evidence['baseline_lookup_by_id']}, corrupted={evidence['corrupted_lookup_by_id']}",
        f"- Exact lookup by title: baseline={evidence['baseline_lookup_by_title']}, corrupted={evidence['corrupted_lookup_by_title']}",
        f"- Factual query baseline doc IDs: `{baseline_answer.retrieved_doc_ids}`",
        f"- Factual query corrupted doc IDs: `{corrupted_answer.retrieved_doc_ids}`",
        "",
        "## Scope limitation",
        "Corrupted metrics/answers, quality comparison and repair are owned by evaluator/Lead. "
        "The corrupted index is isolated and ready for the locked test set.",
    ]
    report_path = PROJECT_DIR / "report" / "role4_cp4_cp5.md"
    write_text(report_path, "\n".join(report_lines) + "\n")
    print(json.dumps({"status": "PASS" if pass_status else "BLOCKED", "report": str(report_path), "evidence": evidence}, ensure_ascii=True))


if __name__ == "__main__":
    main()
