from __future__ import annotations

from datetime import datetime
from typing import Iterable

import pandas as pd

from core.utils import normalize_whitespace
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
    """Return a whitespace-normalized string; null-like values become empty."""
    if value is None or (not isinstance(value, (list, tuple, set, dict)) and pd.isna(value)):
        return ""
    return normalize_whitespace(str(value))


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
    for source_order, record in enumerate(records):
        paper_id = _clean_text(record.paper_id)
        title = _clean_text(record.title)
        if not paper_id or not title:
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

    if not rows:
        return pd.DataFrame(columns=CLEAN_COLUMNS)

    df = pd.DataFrame(rows)
    df["published"] = pd.to_datetime(df["published"], errors="coerce", utc=True)
    df["updated"] = pd.to_datetime(df["updated"], errors="coerce", utc=True)

    # Stable sort makes the last row the newest record and preserves input-order
    # precedence when two records have the same/missing update timestamp.
    df = df.sort_values(["paper_id", "updated", "_source_order"], na_position="first", kind="stable")
    df = df.drop_duplicates(subset="paper_id", keep="last")

    run_timestamp = pd.Timestamp(run_date)
    run_timestamp = run_timestamp.tz_localize("UTC") if run_timestamp.tzinfo is None else run_timestamp.tz_convert("UTC")
    age = (run_timestamp.normalize() - df["published"].dt.normalize()).dt.days
    df["age_days"] = age.clip(lower=0).astype("Int64")

    return df.sort_values(["published", "paper_id"], na_position="last", ascending=[False, True], kind="stable").reset_index(drop=True)[CLEAN_COLUMNS]
