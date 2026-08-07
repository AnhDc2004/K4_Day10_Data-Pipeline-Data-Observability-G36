"""CP6 — Chứng minh từng bản ghi bị hỏng đã phục hồi, bằng lineage chứ không bằng metric.

Nhiệm vụ CP6 của Vai trò 2: "chứng minh record corrupt/drop đã phục hồi bằng
lineage/source evidence".

Báo cáo so sánh của nhóm chứng minh phục hồi ở mức **tổng thể** (Δ metric = 0).
Điều đó chưa loại trừ khả năng một bản ghi vẫn hỏng mà metric không đủ nhạy để
thấy. Script này kiểm ở mức **từng bản ghi**: với mỗi thao tác trong
``corruption_log.json``, xác nhận triệu chứng có thật ở bản corrupted và đã biến
mất ở bản repaired, rồi truy ngược ID về raw snapshot.

Chạy sau ``script/run_corruption_flow.py``:
    python script/p2_checks/cp6_repair_lineage_proof.py
"""

from __future__ import annotations

import json

import pandas as pd

from _common import header, raw_response_dois, section, settings, setup_console, summarize, verdict

NOISE_MARKER = "[CORRUPTED_NOISE]"


def _row(df: pd.DataFrame, paper_id: str) -> pd.Series | None:
    match = df[df["paper_id"] == paper_id]
    return None if match.empty else match.iloc[0]


def prove() -> int:
    cfg = settings()
    results: list[bool] = []

    header("CP6 — BẰNG CHỨNG PHỤC HỒI THEO TỪNG BẢN GHI")

    for path in (cfg.paths.corruption_log, cfg.paths.corrupted_clean_csv, cfg.paths.repaired_clean_csv):
        if not path.exists():
            print(f"   [FAIL] Thiếu '{path}'. Chạy 'python script/run_corruption_flow.py' trước.")
            return 1

    log = json.loads(cfg.paths.corruption_log.read_text(encoding="utf-8"))
    base = pd.read_csv(cfg.paths.clean_csv, dtype={"paper_id": str})
    corr = pd.read_csv(cfg.paths.corrupted_clean_csv, dtype={"paper_id": str})
    rep = pd.read_csv(cfg.paths.repaired_clean_csv, dtype={"paper_id": str})

    section("1/3 · Kiểm từng thao tác corruption")
    for op in log["operations"]:
        results.extend(_check_operation(op, base, corr, rep))

    # --- 2. Repaired có trùng khớp baseline trên toàn bộ trường agent dùng không ---
    section("2/3 · Repaired ↔ baseline trên toàn dataset")
    results.append(verdict(len(rep) == len(base), f"số dòng khớp ({len(rep)} = {len(base)})"))
    fields = ["title", "summary", "published", "authors_joined", "text_for_embedding"]
    merged = base.merge(rep, on="paper_id", suffixes=("_base", "_rep"))
    results.append(verdict(len(merged) == len(base), f"mọi paper_id baseline đều có trong repaired ({len(merged)})"))
    for field in fields:
        left = merged[f"{field}_base"].fillna("").astype(str).str.strip()
        right = merged[f"{field}_rep"].fillna("").astype(str).str.strip()
        mismatched = int((left != right).sum())
        results.append(verdict(mismatched == 0, f"trường '{field}' khớp 100% ({len(merged) - mismatched}/{len(merged)})"))

    # --- 3. Mọi bản ghi repaired truy được về raw response gốc ---
    section("3/3 · Truy ngược repaired → raw response")
    payload = json.loads(cfg.paths.raw_api_response.read_text(encoding="utf-8"))
    dois = raw_response_dois(payload)
    repaired_ids = set(rep["paper_id"].astype(str))
    orphans = sorted(repaired_ids - dois)
    results.append(
        verdict(
            not orphans,
            f"mọi paper_id repaired đều có DOI tương ứng trong raw response ({len(repaired_ids)} ID, mồ côi: {len(orphans)})",
        )
    )
    print("   Diễn giải: repair không sinh dữ liệu mới và không sửa tay — mọi dòng đều")
    print("   dựng lại được từ snapshot Crossref đã lưu trước khi corruption xảy ra.")

    return summarize(results)


def _check_operation(op: dict, base: pd.DataFrame, corr: pd.DataFrame, rep: pd.DataFrame) -> list[bool]:
    """Kiểm một thao tác corruption: triệu chứng có ở corrupted, đã sạch ở repaired."""
    kind = op["type"]
    checks: list[bool] = []
    print(f"\n   • {kind} — {', '.join(op['record_ids'])}")

    for paper_id in op["record_ids"]:
        base_row, corr_row, rep_row = _row(base, paper_id), _row(corr, paper_id), _row(rep, paper_id)

        if kind == "drop_latest":
            checks.append(verdict(corr_row is None, f"  {paper_id[:32]}: đã biến mất ở corrupted (đúng triệu chứng)"))
            checks.append(verdict(rep_row is not None, f"  {paper_id[:32]}: đã quay lại ở repaired"))
            if rep_row is not None and base_row is not None:
                checks.append(
                    verdict(
                        str(rep_row["title"]).strip() == str(base_row["title"]).strip(),
                        f"  {paper_id[:32]}: title phục hồi đúng nguyên bản",
                    )
                )

        elif kind == "missing_summary":
            corrupted_blank = corr_row is None or not str(corr_row["summary"]).strip() or corr_row["summary"] != corr_row["summary"]
            checks.append(verdict(bool(corrupted_blank), f"  {paper_id[:32]}: summary rỗng ở corrupted"))
            if rep_row is not None and base_row is not None:
                checks.append(
                    verdict(
                        str(rep_row["summary"]).strip() == str(base_row["summary"]).strip(),
                        f"  {paper_id[:32]}: summary phục hồi đủ {len(str(base_row['summary']))} ký tự",
                    )
                )

        elif kind == "inject_noise":
            checks.append(
                verdict(
                    corr_row is not None and NOISE_MARKER in str(corr_row["summary"]),
                    f"  {paper_id[:32]}: có noise marker ở corrupted",
                )
            )
            checks.append(
                verdict(
                    rep_row is not None and NOISE_MARKER not in str(rep_row["summary"]),
                    f"  {paper_id[:32]}: noise marker đã sạch ở repaired",
                )
            )

        elif kind == "truncate_title":
            if corr_row is not None and base_row is not None:
                checks.append(
                    verdict(
                        len(str(corr_row["title"])) < len(str(base_row["title"])),
                        f"  {paper_id[:32]}: title bị cắt còn {len(str(corr_row['title']))} ký tự ở corrupted",
                    )
                )
            if rep_row is not None and base_row is not None:
                checks.append(
                    verdict(
                        str(rep_row["title"]).strip() == str(base_row["title"]).strip(),
                        f"  {paper_id[:32]}: title phục hồi đủ {len(str(base_row['title']))} ký tự",
                    )
                )

        elif kind == "old_published_date":
            if corr_row is not None and base_row is not None:
                checks.append(
                    verdict(
                        str(corr_row["published"]) != str(base_row["published"]),
                        f"  {paper_id[:32]}: published bị đẩy lùi ({base_row['published']} → {corr_row['published']})",
                    )
                )
            if rep_row is not None and base_row is not None:
                checks.append(
                    verdict(
                        str(rep_row["published"]) == str(base_row["published"]),
                        f"  {paper_id[:32]}: published phục hồi về {base_row['published']}",
                    )
                )

        elif kind == "add_duplicate":
            corr_count = int((corr["paper_id"] == paper_id).sum())
            rep_count = int((rep["paper_id"] == paper_id).sum())
            checks.append(verdict(corr_count > 1, f"  {paper_id[:32]}: xuất hiện {corr_count} lần ở corrupted"))
            checks.append(verdict(rep_count == 1, f"  {paper_id[:32]}: còn đúng 1 lần ở repaired"))

    return checks


if __name__ == "__main__":
    setup_console()
    raise SystemExit(prove())
