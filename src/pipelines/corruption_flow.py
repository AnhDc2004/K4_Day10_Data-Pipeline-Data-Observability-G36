from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from core import Settings, load_settings, read_json, write_csv
from core.utils import now_utc
from ingestion import load_raw_records, build_clean_dataframe, corrupt_clean_dataframe
from observability import build_freshness_report, run_data_quality_checks, generate_corruption_report
from retrieval import validate_clean_dataframe, LocalEmbeddingIndex
from evaluation import evaluate_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _load_optional_json(*candidates) -> dict | None:
    """Nạp file JSON đầu tiên tìm thấy trong danh sách ứng viên.

    Dùng cho quality/freshness của baseline: hai artifact này do Phase 1 ghi ra và
    tên file phụ thuộc ``report_name`` được truyền vào lúc đó. Thiếu file không phải
    lỗi chặn — comparison report sẽ ghi "không có dữ liệu" ở cột Baseline thay vì
    mặc định coi là ĐẠT.
    """
    for path in candidates:
        if path and Path(path).exists():
            logger.info(f"-> Nạp baseline signal từ '{path}'.")
            return read_json(path)
    logger.warning(
        f"Không tìm thấy baseline signal trong: {[str(c) for c in candidates if c]}. "
        "Cột Baseline của bảng observability sẽ để trống thay vì giả định là ĐẠT."
    )
    return None


def main() -> None:
    """Thực thi Phase 2 Corruption & Repair Pipeline Flow."""
    logger.info("==================================================")
    logger.info(" BẮT ĐẦU CHẠY CORRUPTION -> REPAIR FLOW (PHASE 2) ")
    logger.info("==================================================")

    # -------------------------------------------------------------------------
    # 1. ĐỌC CLEANED BASELINE METRICS & DATASET
    # -------------------------------------------------------------------------
    logger.info("[Step 1/8] Loading baseline settings and clean artifacts...")
    settings = load_settings()

    if not settings.paths.clean_csv.exists():
        raise FileNotFoundError(
            f"[BLOCKER] Không tìm thấy tệp clean baseline tại '{settings.paths.clean_csv}'. "
            "Vui lòng chạy Phase 1 (`python script/run_phase1.py`) trước!"
        )

    df_baseline = pd.read_csv(settings.paths.clean_csv)
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    logger.info(f"-> Nạp thành công {len(df_baseline)} bản ghi baseline clean.")

    # Baseline quality/freshness cho cột Baseline của comparison report.
    # Không nạp thì report buộc phải hard-code "PASSED"/"FRESH" — vi phạm nguyên tắc
    # "report phải trỏ tới artifact thật".
    quality_dir = settings.paths.quality_dir
    baseline_quality = _load_optional_json(
        quality_dir / "phase1-baseline_quality.json",
        quality_dir / "baseline_quality.json",
    )
    baseline_freshness = _load_optional_json(
        getattr(settings.paths, "freshness_report", None),
        quality_dir / "freshness_report.json",
        quality_dir / "baseline_freshness_report.json",
    )

    # -------------------------------------------------------------------------
    # 2. TẠO CORRUPTED DATASET & AUDIT LOG
    # -------------------------------------------------------------------------
    logger.info("[Step 2/8] Generating corrupted dataframe with full scenarios...")
    corruption_log_path = settings.paths.corruption_log
    df_corrupted = corrupt_clean_dataframe(df_baseline, output_log_path=corruption_log_path)

    # -------------------------------------------------------------------------
    # 3. SAVE CORRUPTED ARTIFACTS (PATH ISOLATION)
    # -------------------------------------------------------------------------
    logger.info("[Step 3/8] Writing isolated corrupted artifacts...")
    write_csv(df_corrupted, settings.paths.corrupted_clean_csv)
    logger.info(f"-> Corrupted CSV đã lưu tại path riêng: '{settings.paths.corrupted_clean_csv}'")

    # -------------------------------------------------------------------------
    # 4. REBUILD EMBEDDING & EVALUATE TREN TEST SET CŨ
    # -------------------------------------------------------------------------
    logger.info("[Step 4/8] Rebuilding Corrupted Embedding Index (Collection: 'papers-corrupted')...")
    index_corrupted = LocalEmbeddingIndex.build(
        df=df_corrupted,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )
    logger.info(f"-> Corrupted Index built thành công (collection='{index_corrupted.collection_name}').")

    logger.info("Evaluating pipeline on Corrupted Index...")
    corrupted_eval = evaluate_pipeline(
        settings=settings,
        index=index_corrupted,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )

    # -------------------------------------------------------------------------
    # 5. RUN QUALITY CHECKS & TẠO FRESHNESS REPORT TREN CORRUPTED DATA
    # -------------------------------------------------------------------------
    logger.info("[Step 5/8] Running Data Quality & Freshness checks on Corrupted Data...")
    corrupted_quality = run_data_quality_checks(
        df=df_corrupted,
        settings=settings,
        report_name="corrupted",
    )

    corrupted_freshness_path = settings.paths.quality_dir / "corrupted_freshness_report.json"
    corrupted_freshness = build_freshness_report(
        df=df_corrupted,
        settings=settings,
        report_path=corrupted_freshness_path,
    )

    # -------------------------------------------------------------------------
    # 6. REPAIR LAI TU RAW SOURCE & VALIDATE CONTRACT
    # -------------------------------------------------------------------------
    logger.info("[Step 6/8] Repairing dataset from raw snapshot records...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    
    # Dùng giờ UTC để age_days tái lập được; datetime.now() là giờ local không tzinfo,
    # chạy trên máy khác múi giờ sẽ cho age_days lệch so với baseline.
    run_date = now_utc()
    df_repaired = build_clean_dataframe(raw_records, run_date=run_date)

    # Guard Clause: Dừng ngay nếu vi phạm Data Contract thay vì vá JSON
    logger.info("Validating Repaired Dataframe against Retrieval Contract...")
    contract_check = validate_clean_dataframe(df_repaired)
    
    if contract_check["status"] == "fail":
        hard_failures = contract_check.get("hard_failures", [])
        raise RuntimeError(
            f"[BLOCKER] Repaired dataframe vi phạm Data Contract! Hard Failures: {hard_failures}. "
            "Pipeline dừng lại để yêu cầu sửa logic Data Cleaning/Contract thay vì vá JSON kết quả."
        )

    write_csv(df_repaired, settings.paths.repaired_clean_csv)
    logger.info(f"-> Repaired CSV đã lưu tại path riêng: '{settings.paths.repaired_clean_csv}'")

    # -------------------------------------------------------------------------
    # 7. EVALUATE LAI LAN NUA (REPAIRED DATASET)
    # -------------------------------------------------------------------------
    logger.info("[Step 7/8] Rebuilding Repaired Index (Collection: 'papers-repaired') & Re-evaluating...")
    index_repaired = LocalEmbeddingIndex.build(
        df=df_repaired,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )

    repaired_eval = evaluate_pipeline(
        settings=settings,
        index=index_repaired,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )

    repaired_quality = run_data_quality_checks(
        df=df_repaired,
        settings=settings,
        report_name="repaired",
    )

    repaired_freshness_path = settings.paths.quality_dir / "repaired_freshness_report.json"
    repaired_freshness = build_freshness_report(
        df=df_repaired,
        settings=settings,
        report_path=repaired_freshness_path,
    )

    # -------------------------------------------------------------------------
    # 8. TAO COMPARISON REPORT (MARKDOWN)
    # -------------------------------------------------------------------------
    logger.info("[Step 8/8] Generating Comparison Report (Baseline vs Corrupted vs Repaired)...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_eval.summary,
        repaired_metrics=repaired_eval.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
        baseline_quality=baseline_quality,
        baseline_freshness=baseline_freshness,
    )
    logger.info(f"-> Báo cáo so sánh Markdown hoàn tất tại: '{settings.paths.comparison_report}'")

    logger.info("==================================================")
    logger.info(" PIPELINE PHASE 2 HOÀN THÀNH TẤT CẢ TÁC VỤ!      ")
    logger.info("==================================================")


if __name__ == "__main__":
    main()