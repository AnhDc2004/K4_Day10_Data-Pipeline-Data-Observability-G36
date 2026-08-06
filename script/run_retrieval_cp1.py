from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "src"))

from core.config import load_settings
from retrieval.contract import compare_clean_exports, validate_clean_dataframe
from retrieval.smoke_queries import SMOKE_QUERIES


def _load_json_dataframe(path: Path) -> pd.DataFrame:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"Expected a JSON list in {path}")
    return pd.DataFrame(payload)


def _markdown_report(
    csv_path: Path,
    json_path: Path,
    csv_result: dict,
    json_result: dict,
    export_result: dict,
) -> str:
    sample = csv_result.get("sample_document") or {}
    metadata = sample.get("metadata", {})
    query_names = ", ".join(query.name for query in SMOKE_QUERIES)
    lines = [
        "# Vai trò 4 — CP1 Retrieval Contract Validation",
        "",
        "## Kết quả",
        "",
        f"- CSV: `{csv_path}` ({csv_result['rows']} rows, **{csv_result['status']}**)",
        f"- JSON: `{json_path}` ({json_result['rows']} rows, **{json_result['status']}**)",
        f"- CSV/JSON cùng row count: **{export_result['same_row_count']}**",
        f"- CSV/JSON cùng paper IDs: **{export_result['same_paper_ids']}**",
        "",
        "## Contract checks",
        "",
        "| Check | CSV | JSON |",
        "| --- | ---: | ---: |",
        f"| Required columns missing | {len(csv_result['missing_columns'])} | {len(json_result['missing_columns'])} |",
        f"| Duplicate paper IDs | {csv_result['duplicate_paper_ids']} | {json_result['duplicate_paper_ids']} |",
        f"| Empty paper IDs | {csv_result.get('empty_fields', {}).get('paper_id', 0)} | {json_result.get('empty_fields', {}).get('paper_id', 0)} |",
        f"| Empty titles | {csv_result.get('empty_fields', {}).get('title', 0)} | {json_result.get('empty_fields', {}).get('title', 0)} |",
        f"| Empty text_for_embedding | {csv_result.get('empty_fields', {}).get('text_for_embedding', 0)} | {json_result.get('empty_fields', {}).get('text_for_embedding', 0)} |",
        f"| Empty summaries (warning) | {csv_result.get('empty_summaries', 0)} | {json_result.get('empty_summaries', 0)} |",
        "",
        "## Index configuration",
        "",
        "- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`",
        "- Backend: ChromaDB",
        "- Persist path: `data/chroma/`",
        "- Baseline collection: `papers-baseline`",
        "- Baseline manifest: `data/embeddings/papers_embeddings.json`",
        "- Retrieval `top_k`: `4`",
        "",
        "## Sample document mapping",
        "",
        f"- `record_id`: `{sample.get('record_id', '')}`",
        f"- `paper_id`: `{sample.get('paper_id', '')}`",
        f"- `title`: {sample.get('title', '')}",
        f"- Metadata keys: `{', '.join(metadata.keys())}`",
        "",
        "## CP2 smoke queries",
        "",
        f"`{query_names}`",
        "",
        "## Warnings and next handoff",
        "",
        *[f"- {warning}" for warning in csv_result.get("warnings", [])],
        "- Chưa tạo embedding, Chroma collection hoặc manifest ở CP1.",
        "- Có thể chuyển sang CP2 khi Lead xác nhận contract và clean artifact này.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    settings = load_settings(PROJECT_DIR)
    csv_path = settings.paths.clean_csv
    json_path = settings.paths.clean_json
    report_path = PROJECT_DIR / "report" / "role4_cp1.md"

    csv_df = pd.read_csv(csv_path)
    json_df = _load_json_dataframe(json_path)
    csv_result = validate_clean_dataframe(csv_df)
    json_result = validate_clean_dataframe(json_df)
    export_result = compare_clean_exports(csv_df, json_df)

    report_path.write_text(
        _markdown_report(csv_path, json_path, csv_result, json_result, export_result),
        encoding="utf-8",
    )

    hard_failure = (
        csv_result["status"] != "pass"
        or json_result["status"] != "pass"
        or not export_result["same_row_count"]
        or not export_result["same_paper_ids"]
    )
    print(f"CP1 report: {report_path}")
    print(f"CSV rows: {csv_result['rows']}; JSON rows: {json_result['rows']}")
    print(f"Contract status: {'FAIL' if hard_failure else 'PASS'}")
    if hard_failure:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

