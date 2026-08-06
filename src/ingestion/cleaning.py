from __future__ import annotations

from datetime import datetime
from html import unescape
import json
from pathlib import Path
import re
from typing import Iterable

import pandas as pd

from core.utils import normalize_whitespace, write_csv, write_json
from ingestion.crossref import PaperRecord


CLEAN_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "authors",
    "categories",
    "primary_category",
    "published",
    "updated",
    "age_days",
    "authors_joined",
    "categories_joined",
    "summary_chars",
    "text_for_embedding",
    "abs_url",
    "pdf_url",
    "comment",
]


def _clean_text(value: object) -> str:
    """Normalize Crossref text, including JATS/HTML tags and encoded entities."""
    if value is None or (not isinstance(value, (list, tuple, set, dict)) and pd.isna(value)):
        return ""
    text = unescape(str(value))
    text = re.sub(r"<[^>]+>", "", text)
    return normalize_whitespace(text)


def _clean_list(values: Iterable[object] | None) -> list[str]:
    """Normalize, remove empty values, and deduplicate while preserving order."""
    if values is None or isinstance(values, (str, bytes)):
        values = [values] if values else []

    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean_text(value)
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


def _embedding_text(title: str, summary: str, authors: str, categories: str) -> str:
    """Build stable, labelled text so an embedding keeps field semantics."""
    parts = [f"Title: {title}"]
    if summary:
        parts.append(f"Summary: {summary}")
    if authors:
        parts.append(f"Authors: {authors}")
    if categories:
        parts.append(f"Categories: {categories}")
    return "\n".join(parts)


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into the canonical dataframe used by the pipeline.

    Rows without ``paper_id`` or ``title`` are rejected. Invalid dates are kept
    as ``NaT`` so missingness remains observable. Duplicate IDs keep the record
    with the most recent valid ``updated`` timestamp (input order breaks ties).
    """
    rows: list[dict[str, object]] = []
    dropped_missing_paper_id = 0
    dropped_missing_title = 0
    for source_order, record in enumerate(records):
        paper_id = _clean_text(record.paper_id)
        title = _clean_text(record.title)
        if not paper_id:
            dropped_missing_paper_id += 1
            continue
        if not title:
            dropped_missing_title += 1
            continue

        summary = _clean_text(record.summary)
        authors = _clean_list(record.authors)
        categories = _clean_list(record.categories)
        primary_category = _clean_text(record.primary_category)
        if primary_category and primary_category.casefold() not in {item.casefold() for item in categories}:
            categories.insert(0, primary_category)

        authors_joined = ", ".join(authors)
        categories_joined = ", ".join(categories)
        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": record.published,
                "updated": record.updated,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "text_for_embedding": _embedding_text(title, summary, authors_joined, categories_joined),
                "abs_url": _clean_text(record.abs_url),
                "pdf_url": _clean_text(record.pdf_url),
                "comment": _clean_text(record.comment),
                "_source_order": source_order,
            }
        )

    report: dict[str, int] = {
        "input_records": len(records),
        "dropped_missing_paper_id": dropped_missing_paper_id,
        "dropped_missing_title": dropped_missing_title,
        "filtered_records": dropped_missing_paper_id + dropped_missing_title,
        "duplicates_removed": 0,
        "invalid_published_dates": 0,
        "empty_summaries": 0,
        "output_records": 0,
    }
    if not rows:
        empty_df = pd.DataFrame(columns=CLEAN_COLUMNS)
        empty_df.attrs["cleaning_report"] = report
        return empty_df

    df = pd.DataFrame(rows)
    df["published"] = pd.to_datetime(df["published"], errors="coerce", utc=True, format="mixed")
    df["updated"] = pd.to_datetime(df["updated"], errors="coerce", utc=True, format="mixed")
    report["invalid_published_dates"] = int(df["published"].isna().sum())
    report["empty_summaries"] = int(df["summary"].eq("").sum())

    df = df.sort_values(["paper_id", "updated", "_source_order"], na_position="first", kind="stable")
    before_dedupe = len(df)
    df = df.drop_duplicates(subset="paper_id", keep="last")
    report["duplicates_removed"] = before_dedupe - len(df)

    run_timestamp = pd.Timestamp(run_date)
    run_timestamp = run_timestamp.tz_localize("UTC") if run_timestamp.tzinfo is None else run_timestamp.tz_convert("UTC")
    age = (run_timestamp.normalize() - df["published"].dt.normalize()).dt.days
    df["age_days"] = age.clip(lower=0).astype("Int64")

    result = df.sort_values(
        ["published", "paper_id"], na_position="last", ascending=[False, True], kind="stable"
    ).reset_index(drop=True)[CLEAN_COLUMNS]
    report["output_records"] = len(result)
    result.attrs["cleaning_report"] = report
    return result


def write_clean_artifacts(
    df: pd.DataFrame,
    csv_path: Path,
    json_path: Path,
    report_path: Path,
) -> dict[str, int]:
    """Write clean CSV/JSON plus the auditable filter/dedupe count report."""
    missing_columns = [column for column in CLEAN_COLUMNS if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Clean dataframe is missing columns: {missing_columns}")

    report = dict(df.attrs.get("cleaning_report", {}))
    if not report:
        raise ValueError("Cleaning report is missing; use build_clean_dataframe before writing artifacts.")

    write_csv(df, csv_path)
    json_records = json.loads(df.to_json(orient="records", date_format="iso"))
    write_json(json_path, json_records)
    write_json(report_path, report)
    return report
