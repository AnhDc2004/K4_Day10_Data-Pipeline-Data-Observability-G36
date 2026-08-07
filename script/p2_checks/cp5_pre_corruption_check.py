"""CP5 — Xác nhận raw nguyên vẹn và corruption ghi ra path riêng.

Ba nhiệm vụ CP5 của Vai trò 2:
  1. Raw source còn nguyên vẹn trước khi corrupt clean data.
  2. Chọn bản ghi có lineage rõ để chứng minh có thể repair.
  3. Corrupted flow không fetch nguồn mới làm comparison mất công bằng.

Bản gốc kiểm tra mục 1 bằng ``raw_dir.exists()`` — thư mục rỗng vẫn cho "OK", và
mục 2 lấy ``data[0]`` của file clean bất kỳ, tức bản ghi được chọn không liên
quan gì tới corruption thật sự xảy ra. Bản này đối chiếu vân tay sha256 cho mục 1
và đọc ``corruption_log.json`` cho mục 2.

Chạy sau ``script/run_corruption_flow.py``:
    python script/p2_checks/cp5_pre_corruption_check.py
"""

from __future__ import annotations

import json

import pandas as pd

from _common import header, section, settings, setup_console, sha256_of, summarize, verdict
from cp3_verify_raw import INTEGRITY_FILENAME


def check() -> int:
    cfg = settings()
    results: list[bool] = []

    header("CP5 — RAW NGUYÊN VẸN & CÔ LẬP CORRUPTION")

    # --- 1. Raw còn nguyên vẹn (so vân tay, không chỉ kiểm tra tồn tại) ---
    section("1/3 · Toàn vẹn raw source")
    recorded_path = cfg.paths.quality_dir / INTEGRITY_FILENAME
    if recorded_path.exists():
        recorded = json.loads(recorded_path.read_text(encoding="utf-8"))
        for key, path in (
            ("raw_api_response", cfg.paths.raw_api_response),
            ("raw_records", cfg.paths.raw_records_json),
        ):
            current = sha256_of(path)
            results.append(
                verdict(
                    current == recorded.get(key, {}).get("sha256"),
                    f"'{path.name}' giữ nguyên sha256 sau khi chạy corruption flow",
                )
            )
    else:
        results.append(verdict(False, f"chưa có '{INTEGRITY_FILENAME}' — chạy cp3_verify_raw.py trước"))

    # --- 2. Corruption ghi ra path riêng, không đè baseline ---
    section("2/3 · Cô lập artifact")
    baseline_paths = {cfg.paths.clean_csv, cfg.paths.embeddings_json}
    corrupted_paths = {cfg.paths.corrupted_clean_csv, cfg.paths.corrupted_embeddings_json}
    results.append(
        verdict(
            not (baseline_paths & corrupted_paths),
            "corrupted dùng path tách rời baseline (không ghi đè)",
        )
    )
    results.append(
        verdict(
            cfg.baseline_collection_name != cfg.corrupted_collection_name,
            f"collection tách rời: '{cfg.baseline_collection_name}' ≠ '{cfg.corrupted_collection_name}'",
        )
    )
    if cfg.paths.corrupted_clean_csv.exists():
        df_base = pd.read_csv(cfg.paths.clean_csv, dtype={"paper_id": str})
        df_corr = pd.read_csv(cfg.paths.corrupted_clean_csv, dtype={"paper_id": str})
        print(f"   baseline : {len(df_base)} dòng · corrupted: {len(df_corr)} dòng")
        results.append(verdict(len(df_base) == 24, "file baseline vẫn đủ 24 dòng — corruption không chạm vào"))

    # --- 3. Bản ghi được chọn để chứng minh repair phải truy được về raw ---
    section("3/3 · Mẫu chứng minh khả năng repair")
    log_path = cfg.paths.corruption_log
    if not log_path.exists():
        results.append(verdict(False, f"chưa có '{log_path.name}' — chạy run_corruption_flow.py trước"))
        return summarize(results)

    log = json.loads(log_path.read_text(encoding="utf-8"))
    raw_ids = {r["paper_id"] for r in json.loads(cfg.paths.raw_records_json.read_text(encoding="utf-8"))}

    print(f"   corruption_log: {log['baseline_count']} → {log['corrupted_count']} dòng, {len(log['operations'])} thao tác")
    affected: list[str] = []
    for op in log["operations"]:
        affected.extend(op["record_ids"])
        print(f"      {op['type']:20s} {', '.join(op['record_ids'])}")

    traceable = [pid for pid in affected if pid in raw_ids]
    results.append(
        verdict(
            len(traceable) == len(affected),
            f"mọi bản ghi bị corrupt đều truy được về raw snapshot ({len(traceable)}/{len(affected)}) → repair được",
        )
    )

    return summarize(results)


if __name__ == "__main__":
    setup_console()
    raise SystemExit(check())
