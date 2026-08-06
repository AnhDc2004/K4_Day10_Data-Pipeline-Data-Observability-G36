from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

# 1. Core Utilities & Settings
from core.config import Settings, load_settings
from core.utils import read_csv, read_json, write_csv

# 2. Ingestion & Cleaning
from cleaning import build_clean_dataframe, write_clean_artifacts
from ingestion.crossref import load_raw_records

# 3. Observability & Data Quality
from quality import build_freshness_report, run_data_quality_checks

# 4. Retrieval, Indexing & Contract Validation
from retrieval.contract import validate_clean_dataframe
from retrieval.index import LocalEmbeddingIndex

# 5. Evaluation & Reporting
from evaluation import evaluate_pipeline
from reporting import generate_corruption_report

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def create_corrupted_dataframe(df_baseline: pd.DataFrame) -> pd.DataFrame:
    """Tạo dữ liệu lỗi cố ý (Corrupted) từ Baseline để kiểm thử Observability & Resilience.
    
    Các lỗi mô phỏng:
    - Mất Title/Summary (Gây đứt gãy embedding semantic).
    - Làm sai lệch ngày xuất bản (Kích hoạt cảnh báo Freshness).
    """
    df_corrupted = df_baseline.copy()

    if len(df_corrupted) > 0:
        # Mô phỏng lỗi missing title & empty summary
        df_corrupted.loc[0, "title"] = ""
        if len(df_corrupted) > 1:
            df_corrupted.loc[1, "summary"] = ""
            df_corrupted.loc[1, "summary_chars"] = 0
            df_corrupted.loc[1, "text_for_embedding"] = f"Title: {df_corrupted.loc[1, 'title']}"

    if "published" in df_corrupted.columns and len(df_corrupted) > 2:
        # Mô phỏng dữ liệu quá cũ (Stale)
        df_corrupted.loc[2, "published"] = "2010-01-01"
        df_corrupted.loc[2, "age_days"] = 5000

    return df_corrupted


def main() -> None:
    """Thực thi Phase 2 Corruption & Repair Pipeline Flow."""
    logger.info("==================================================")
    logger.info(" BẮT ĐẦU CHẠY CORRUPTION -> REPAIR FLOW (PHASE 2) ")
    logger.info("==================================================")

    # -------------------------------------------------------------------------
    # 1. LOAD BASELINE METRICS & CLEAN DATASET
    # -------------------------------------------------------------------------
    logger.info("[Step 1/8] Loading baseline settings and clean artifacts...")
    settings = load_settings()

    if not settings.paths.clean_csv.exists():
        raise FileNotFoundError(
            f"[BLOCKER] Không tìm thấy tệp clean baseline tại '{settings.paths.clean_csv}'. "
            "Vui lòng chạy Phase 1 (`python script/run_phase1.py`) trước!"
        )

    df_baseline = read_csv(settings.paths.clean_csv)
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    logger.info(f"-> Nạp thành công {len(df_baseline)} bản ghi baseline clean.")

    # -------------------------------------------------------------------------
    # 2. CREATE CORRUPTED DATAFRAME
    # -------------------------------------------------------------------------
    logger.info("[Step 2/8] Generating corrupted dataframe...")
    df_corrupted = create_corrupted_dataframe(df_baseline)

    # -------------------------------------------------------------------------
    # 3. SAVE CORRUPTED ARTIFACTS (PATH ISOLATION - KHÔNG GHI ĐÈ BASELINE)
    # -------------------------------------------------------------------------
    logger.info("[Step 3/8] Writing isolated corrupted artifacts...")
    write_csv(df_corrupted, settings.paths.corrupted_clean_csv)
    logger.info(f"-> Corrupted CSV đã lưu tại path riêng: '{settings.paths.corrupted_clean_csv}'")

    # -------------------------------------------------------------------------
    # 4. REBUILD CORRUPTED INDEX & EVALUATE (COLLECTION ISOLATION)
    # -------------------------------------------------------------------------
    logger.info("[Step 4/8] Building Corrupted Index (Collection: 'papers-corrupted')...")
    index_corrupted = LocalEmbeddingIndex.build(
        df=df_corrupted,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,  # Tên Collection: "papers-corrupted"
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
    # 5. RUN QUALITY CHECKS & FRESHNESS ON CORRUPTED DATA
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
    # 6. REPAIR DATA FROM RAW RECORDS & VALIDATE CONTRACT (STOP ON FAILURE)
    # -------------------------------------------------------------------------
    logger.info("[Step 6/8] Repairing dataset from raw snapshot records...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    
    run_date = datetime.now()
    df_repaired = build_clean_dataframe(raw_records, run_date=run_date)

    # STOPS TO FIX DATA CONTRACT: Kiểm tra ngặt nghèo hợp đồng dữ liệu
    logger.info("Validating Repaired Dataframe against Retrieval Contract...")
    contract_check = validate_clean_dataframe(df_repaired)
    
    if contract_check["status"] == "fail":
        # DỪNG PIPELINE ĐỂ SỬA CODE/CONTRACT THAY VÌ VÁ FILE JSON
        hard_failures = contract_check.get("hard_failures", [])
        raise RuntimeError(
            f"[BLOCKER] Repaired dataframe vi phạm Data Contract! Hard Failures: {hard_failures}. "
            "Pipeline dừng lại để yêu cầu sửa logic Data Cleaning/Contract thay vì vá JSON kết quả."
        )

    # Lưu artifacts repaired tại PATH RÊNG
    write_csv(df_repaired, settings.paths.repaired_clean_csv)
    logger.info(f"-> Repaired CSV đã lưu tại path riêng: '{settings.paths.repaired_clean_csv}'")

    # -------------------------------------------------------------------------
    # 7. EVALUATE REPAIRED DATASET (COLLECTION ISOLATION)
    # -------------------------------------------------------------------------
    logger.info("[Step 7/8] Building Repaired Index (Collection: 'papers-repaired') & Evaluating...")
    index_repaired = LocalEmbeddingIndex.build(
        df=df_repaired,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,  # Tên Collection: "papers-repaired"
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
    # 8. GENERATE COMPARISON REPORT (MARKDOWN)
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
    )
    logger.info(f"-> Báo cáo so sánh Markdown hoàn tất tại: '{settings.paths.comparison_report}'")

    logger.info("==================================================")
    logger.info(" PIPELINE PHASE 2 HOÀN THÀNH TẤT CẢ TÁC VỤ!      ")
    logger.info("==================================================")


if __name__ == "__main__":
    main()