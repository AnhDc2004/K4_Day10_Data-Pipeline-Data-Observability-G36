"""Validation helpers for the clean-data to retrieval handoff."""

from __future__ import annotations

from typing import Any

import pandas as pd


RETRIEVAL_REQUIRED_COLUMNS = (
    "paper_id",
    "title",
    "summary",
    "authors_joined",
    "categories_joined",
    "published",
    "abs_url",
    "pdf_url",
    "text_for_embedding",
)

INDEX_METADATA_COLUMNS = (
    "paper_id",
    "title",
    "summary",
    "published",
    "authors_joined",
    "categories_joined",
    "abs_url",
    "pdf_url",
)


def _empty_mask(series: pd.Series) -> pd.Series:
    return series.isna() | series.astype("string").str.strip().eq("")


def build_document_preview(row: pd.Series, index: int) -> dict[str, Any]:
    """Build the retrieval document shape without creating an embedding index."""
    return {
        "record_id": f"{row['paper_id']}::{index}",
        "paper_id": row["paper_id"],
        "title": row["title"],
        "content": row["text_for_embedding"],
        "metadata": {column: row[column] for column in INDEX_METADATA_COLUMNS},
    }


def validate_clean_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    """Validate the clean dataframe required by ``LocalEmbeddingIndex``.

    The result separates hard failures from observable data-quality warnings.
    In particular, an empty summary is reported but does not invalidate the
    retrieval contract when the title still supplies embedding content.
    """
    missing_columns = [column for column in RETRIEVAL_REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        return {
            "status": "fail",
            "rows": int(len(df)),
            "missing_columns": missing_columns,
            "duplicate_paper_ids": 0,
            "empty_fields": {},
            "sample_document": None,
            "warnings": [],
        }

    empty_fields = {
        column: int(_empty_mask(df[column]).sum())
        for column in ("paper_id", "title", "text_for_embedding")
    }
    duplicate_paper_ids = int(df["paper_id"].astype("string").duplicated(keep=False).sum())
    empty_summary = int(_empty_mask(df["summary"]).sum())
    warnings: list[str] = []
    if empty_summary:
        warnings.append(f"{empty_summary} record(s) have an empty summary.")

    hard_failures = [
        field for field in ("paper_id", "title", "text_for_embedding") if empty_fields[field]
    ]
    if duplicate_paper_ids:
        hard_failures.append("duplicate_paper_ids")

    sample_document = None
    if len(df):
        sample_document = build_document_preview(df.iloc[0], 0)

    return {
        "status": "fail" if hard_failures else "pass",
        "rows": int(len(df)),
        "missing_columns": [],
        "duplicate_paper_ids": duplicate_paper_ids,
        "empty_fields": empty_fields,
        "empty_summaries": empty_summary,
        "hard_failures": hard_failures,
        "sample_document": sample_document,
        "warnings": warnings,
    }


def compare_clean_exports(csv_df: pd.DataFrame, json_df: pd.DataFrame) -> dict[str, Any]:
    """Check that CSV and JSON exports have the same retrieval identity set."""
    csv_ids = set(csv_df.get("paper_id", pd.Series(dtype="string")).dropna().astype(str))
    json_ids = set(json_df.get("paper_id", pd.Series(dtype="string")).dropna().astype(str))
    return {
        "same_row_count": len(csv_df) == len(json_df),
        "same_paper_ids": csv_ids == json_ids,
        "csv_only_paper_ids": sorted(csv_ids - json_ids),
        "json_only_paper_ids": sorted(json_ids - csv_ids),
    }

