"""CP3 — So sánh số bản ghi raw ↔ clean và giải thích chênh lệch bằng artifact.

Nhiệm vụ CP3 của Vai trò 2 yêu cầu "nêu rõ chênh lệch có lý do". Bản gốc in sẵn
ba lý do chung chung (dedup / thiếu field / chuẩn hoá) bất kể chênh lệch thực tế
là bao nhiêu — kể cả khi chênh lệch bằng 0. Bản này đọc lý do thật từ
``data/quality/cleaning_report.json`` do cleaning owner ghi ra, và đối chiếu
tổng các nguyên nhân có giải thích hết chênh lệch hay không.

Chạy:
    python script/p2_checks/cp3_compare_counts.py
"""

from __future__ import annotations

import json

import pandas as pd

from _common import header, section, settings, setup_console, summarize, verdict

# Các trường trong cleaning_report.json thực sự làm giảm số dòng.
# 'empty_summaries' và 'invalid_published_dates' là cảnh báo chất lượng, không
# phải thao tác xoá — cộng chúng vào sẽ ra chênh lệch ảo.
DROP_FIELDS = (
    "dropped_missing_paper_id",
    "dropped_missing_title",
    "filtered_records",
    "duplicates_removed",
)


def compare_counts() -> int:
    cfg = settings()
    results: list[bool] = []

    header("CP3 — SO SÁNH RAW ↔ CLEAN COUNT")

    records = json.loads(cfg.paths.raw_records_json.read_text(encoding="utf-8"))
    df_clean = pd.read_csv(cfg.paths.clean_csv, dtype={"paper_id": str})
    raw_count, clean_count = len(records), len(df_clean)
    diff = raw_count - clean_count

    section("1/3 · Số lượng")
    print(f"   raw records  : {raw_count}")
    print(f"   clean records: {clean_count}")
    print(f"   chênh lệch   : {diff} ({diff / raw_count * 100:.2f}%)" if raw_count else "   chênh lệch: n/a")

    # --- 2. Chênh lệch có được giải thích bằng artifact không ---
    section("2/3 · Đối chiếu với cleaning_report.json")
    report_path = cfg.paths.quality_dir / "cleaning_report.json"
    if not report_path.exists():
        results.append(verdict(False, f"thiếu '{report_path}' — không có căn cứ giải thích chênh lệch"))
        return summarize(results)

    report = json.loads(report_path.read_text(encoding="utf-8"))
    explained = 0
    for field in DROP_FIELDS:
        value = int(report.get(field, 0))
        explained += value
        marker = "•" if value == 0 else "→"
        print(f"   {marker} {field:28s}: {value}")
    print(f"   {'tổng số dòng bị loại':30s}: {explained}")

    results.append(
        verdict(
            explained == diff,
            f"cleaning_report giải thích trọn vẹn chênh lệch ({explained} = {diff})",
        )
    )
    results.append(
        verdict(
            int(report.get("input_records", -1)) == raw_count,
            f"cleaning_report.input_records ({report.get('input_records')}) khớp số raw record ({raw_count})",
        )
    )
    results.append(
        verdict(
            int(report.get("output_records", -1)) == clean_count,
            f"cleaning_report.output_records ({report.get('output_records')}) khớp số clean record ({clean_count})",
        )
    )

    # --- 3. Không chỉ đếm: kiểm tra đúng những ID nào bị mất ---
    section("3/3 · Đối chiếu theo paper_id")
    raw_ids = {r["paper_id"] for r in records}
    clean_ids = set(df_clean["paper_id"].astype(str))
    lost = sorted(raw_ids - clean_ids)
    gained = sorted(clean_ids - raw_ids)

    results.append(verdict(not gained, f"clean không có ID nào ngoài raw (phát sinh: {len(gained)})"))
    if lost:
        print(f"   {len(lost)} paper_id có ở raw nhưng không có ở clean:")
        for paper_id in lost[:10]:
            print(f"        - {paper_id}")
    else:
        print("   Không có paper_id nào bị mất giữa raw và clean.")

    if diff == 0:
        print("\n   Diễn giải: cleaning giữ nguyên 100% bản ghi — dữ liệu Crossref lấy về đã đạt")
        print("   mọi điều kiện hợp lệ (có DOI, có title, không trùng, ngày parse được).")

    return summarize(results)


if __name__ == "__main__":
    setup_console()
    raise SystemExit(compare_counts())
