from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import now_utc, write_json
from ingestion.cleaning import _embedding_text

# Moi corruption deu deterministic: chon row theo vi tri on dinh, khong dung random,
# de chay lai cho ra dung mot corrupted dataset va comparison con tai lap duoc.
DROP_LATEST = 2
BLANK_SUMMARY = 3
NOISE_SUMMARY = 3
TRUNCATE_TITLE = 3
STALE_DATE = 3
DUPLICATE_ROWS = 2

TITLE_KEEP_CHARS = 15
STALE_EXTRA_DAYS = 2000
NOISE_TEXT = "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor"


def _rebuild_embedding_text(row: pd.Series) -> str:
    return _embedding_text(
        str(row.get("title") or ""),
        str(row.get("summary") or ""),
        str(row.get("authors_joined") or ""),
        str(row.get("categories_joined") or ""),
    )


def _preview(value: Any, limit: int = 60) -> str:
    text = "" if value is None else str(value)
    return text[:limit] + ("..." if len(text) > limit else "")


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate cac dang data corruption co chu dich tren cleaned dataframe.

    Baseline khong bi cham vao: ham nhan mot copy, tra ve dataframe moi, va ghi
    corruption log ghi ro tung record bi dong vao dau.
    """
    working = df.copy().reset_index(drop=True)
    rows_before = len(working)
    entries: list[dict[str, Any]] = []
    touched: set[int] = set()

    def take(count: int) -> list[int]:
        """Chon `count` vi tri chua bi corruption nao khac dong vao."""
        picked = [index for index in range(len(working)) if index not in touched][:count]
        touched.update(picked)
        return picked

    # 1. Drop mot so record moi nhat. Clean data da sort published giam dan nen day la top rows.
    drop_positions = list(range(min(DROP_LATEST, len(working))))
    for position in drop_positions:
        row = working.loc[position]
        entries.append(
            {
                "type": "drop_latest_record",
                "paper_id": str(row["paper_id"]),
                "parameter": "top-N moi nhat",
                "before": _preview(row["published"]),
                "after": "<removed>",
            }
        )
    working = working.drop(index=drop_positions).reset_index(drop=True)

    # 2. Blank summary.
    for position in take(BLANK_SUMMARY):
        row = working.loc[position]
        entries.append(
            {
                "type": "blank_summary",
                "paper_id": str(row["paper_id"]),
                "parameter": "summary -> chuoi rong",
                "before": f"{len(str(row['summary']))} chars",
                "after": "0 chars",
            }
        )
        working.loc[position, "summary"] = ""
        working.loc[position, "summary_chars"] = 0

    # 3. Them noise vao summary (van co do dai, nhung noi dung bi loang).
    for position in take(NOISE_SUMMARY):
        row = working.loc[position]
        before = str(row["summary"])
        after = f"{NOISE_TEXT} {before} {NOISE_TEXT}"
        entries.append(
            {
                "type": "noise_summary",
                "paper_id": str(row["paper_id"]),
                "parameter": f"chen {len(NOISE_TEXT)} ky tu noise moi dau",
                "before": f"{len(before)} chars",
                "after": f"{len(after)} chars",
            }
        )
        working.loc[position, "summary"] = after
        working.loc[position, "summary_chars"] = len(after)

    # 4. Truncate title -> pha exact lookup theo title.
    for position in take(TRUNCATE_TITLE):
        row = working.loc[position]
        before = str(row["title"])
        after = before[:TITLE_KEEP_CHARS]
        entries.append(
            {
                "type": "truncate_title",
                "paper_id": str(row["paper_id"]),
                "parameter": f"giu {TITLE_KEEP_CHARS} ky tu dau",
                "before": _preview(before),
                "after": _preview(after),
            }
        )
        working.loc[position, "title"] = after

    # 5. Lam published cu di -> pha freshness.
    for position in take(STALE_DATE):
        row = working.loc[position]
        before_published = pd.to_datetime(row["published"], errors="coerce", utc=True)
        after_published = before_published - pd.Timedelta(days=STALE_EXTRA_DAYS)
        before_age = row["age_days"]
        entries.append(
            {
                "type": "stale_published_date",
                "paper_id": str(row["paper_id"]),
                "parameter": f"-{STALE_EXTRA_DAYS} ngay",
                "before": f"{_preview(before_published)} (age {before_age})",
                "after": f"{_preview(after_published)} (age {before_age + STALE_EXTRA_DAYS if pd.notna(before_age) else 'NA'})",
            }
        )
        working.loc[position, "published"] = str(after_published)
        if pd.notna(before_age):
            working.loc[position, "age_days"] = int(before_age) + STALE_EXTRA_DAYS

    # 6. Them duplicate rows -> pha uniqueness va chiem cho trong top-k.
    duplicate_positions = [index for index in range(len(working))][:DUPLICATE_ROWS]
    duplicates = working.loc[duplicate_positions].copy()
    for position in duplicate_positions:
        entries.append(
            {
                "type": "duplicate_row",
                "paper_id": str(working.loc[position, "paper_id"]),
                "parameter": "nhan ban nguyen row",
                "before": "1 row",
                "after": "2 rows",
            }
        )

    # 7. Rebuild text_for_embedding cho moi row da bi doi title/summary.
    working["text_for_embedding"] = working.apply(_rebuild_embedding_text, axis=1)
    duplicates["text_for_embedding"] = duplicates.apply(_rebuild_embedding_text, axis=1)
    corrupted = pd.concat([working, duplicates], ignore_index=True)

    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry["type"]] = counts.get(entry["type"], 0) + 1

    payload = {
        "generated_at": now_utc().isoformat(),
        "deterministic": True,
        "rows_before": rows_before,
        "rows_after": len(corrupted),
        "counts_by_type": counts,
        "affected_paper_ids": sorted({entry["paper_id"] for entry in entries}),
        "entries": entries,
    }
    write_json(output_log_path, payload)

    corrupted.attrs["corruption_log"] = payload
    return corrupted
