from __future__ import annotations

from datetime import UTC
from pathlib import Path
from typing import Any

import pandas as pd

from core import now_utc, write_json
from ingestion import _embedding_text


NOISE_MARKER = "[CORRUPTED_NOISE] irrelevant tokens xqzv qqq 000"


def _require_columns(df: pd.DataFrame) -> None:
    required = {
        "paper_id",
        "title",
        "summary",
        "authors_joined",
        "categories_joined",
        "published",
        "age_days",
        "summary_chars",
        "text_for_embedding",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Clean dataframe is missing corruption contract columns: {missing}")


def _operation(
    corruption_type: str,
    record_ids: list[str],
    parameter: dict[str, Any],
    before_count: int,
    after_count: int,
) -> dict[str, Any]:
    return {
        "type": corruption_type,
        "record_ids": record_ids,
        "parameter": parameter,
        "before_count": before_count,
        "after_count": after_count,
    }


def _rebuild_derived_fields(df: pd.DataFrame) -> None:
    """Tái tạo các trường phái sinh (summary_chars, text_for_embedding) sau khi làm hỏng dữ liệu."""
    df["summary_chars"] = df["summary"].fillna("").astype(str).str.len()
    df["text_for_embedding"] = df.apply(
        lambda row: _embedding_text(
            str(row["title"]),
            str(row["summary"] or ""),
            str(row["authors_joined"] or ""),
            str(row["categories_joined"] or ""),
        ),
        axis=1,
    )
    df["published"] = pd.to_datetime(df["published"], errors="coerce", utc=True).dt.strftime("%Y-%m-%d")


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Tạo bản sao dữ liệu bị corrupt theo các kịch bản cố định và ghi audit log.

    Baseline dataframe không bao giờ bị thay đổi trực tiếp (Immutability).
    """
    _require_columns(df)
    if len(df) < 7:
        raise ValueError("At least 7 clean rows are required for independent corruption scenarios.")

    corrupted = df.copy(deep=True)
    corrupted["published"] = pd.to_datetime(corrupted["published"], errors="coerce", utc=True, format="mixed")
    operations: list[dict[str, Any]] = []
    baseline_count = len(corrupted)

    # 1. Remove two latest records (Xóa một số latest records)
    before = len(corrupted)
    latest_indices = corrupted.sort_values("published", ascending=False, na_position="last").head(2).index
    latest_ids = corrupted.loc[latest_indices, "paper_id"].astype(str).tolist()
    corrupted = corrupted.drop(index=latest_indices).reset_index(drop=True)
    operations.append(
        _operation(
            "drop_latest",
            latest_ids,
            {"count": 2, "sort_field": "published", "order": "descending"},
            before,
            len(corrupted),
        )
    )

    candidate_indices = corrupted.sort_values("paper_id", kind="stable").index.tolist()

    # 2. Blank one summary (Blank summary)
    index = candidate_indices[0]
    paper_id = str(corrupted.at[index, "paper_id"])
    before = len(corrupted)
    corrupted.at[index, "summary"] = ""
    operations.append(_operation("missing_summary", [paper_id], {"replacement": ""}, before, len(corrupted)))

    # 3. Inject noise marker (Add noise vào summary)
    index = candidate_indices[1]
    paper_id = str(corrupted.at[index, "paper_id"])
    before = len(corrupted)
    original_summary = str(corrupted.at[index, "summary"] or "")
    corrupted.at[index, "summary"] = f"{original_summary} {NOISE_MARKER}".strip()
    operations.append(
        _operation("inject_noise", [paper_id], {"marker": NOISE_MARKER, "target_field": "summary"}, before, len(corrupted))
    )

    # 4. Truncate title (Truncate title)
    index = candidate_indices[2]
    paper_id = str(corrupted.at[index, "paper_id"])
    before = len(corrupted)
    original_title = str(corrupted.at[index, "title"] or "")
    corrupted.at[index, "title"] = original_title[:15] if len(original_title) > 15 else original_title
    operations.append(
        _operation("truncate_title", [paper_id], {"max_chars": 15, "original": original_title}, before, len(corrupted))
    )

    # 5. Age one paper by 2 years (Làm stale publication date)
    index = candidate_indices[3]
    paper_id = str(corrupted.at[index, "paper_id"])
    before = len(corrupted)
    days_shift = 730
    previous_date = corrupted.at[index, "published"]
    corrupted.at[index, "published"] = previous_date - pd.Timedelta(days=days_shift)
    current_age = pd.to_numeric(pd.Series([corrupted.at[index, "age_days"]]), errors="coerce").iloc[0]
    corrupted.at[index, "age_days"] = int(current_age + days_shift) if pd.notna(current_age) else pd.NA
    operations.append(
        _operation(
            "old_published_date",
            [paper_id],
            {"days_shifted_back": days_shift, "previous_published": previous_date.isoformat()},
            before,
            len(corrupted),
        )
    )

    # 6. Add exact duplicate row (Add duplicate rows)
    index = candidate_indices[4]
    paper_id = str(corrupted.at[index, "paper_id"])
    before = len(corrupted)
    duplicate = corrupted.loc[[index]].copy(deep=True)
    corrupted = pd.concat([corrupted, duplicate], ignore_index=True)
    operations.append(_operation("add_duplicate", [paper_id], {"copies_added": 1}, before, len(corrupted)))

    _rebuild_derived_fields(corrupted)
    log = {
        "generated_at": now_utc().isoformat(),
        "baseline_count": baseline_count,
        "corrupted_count": len(corrupted),
        "operations": operations,
    }
    write_json(Path(output_log_path), log)
    corrupted.attrs["corruption_log"] = log
    return corrupted