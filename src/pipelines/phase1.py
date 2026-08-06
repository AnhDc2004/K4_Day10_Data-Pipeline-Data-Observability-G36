from __future__ import annotations

from datetime import datetime
import logging

import pandas as pd

from core import load_settings, read_json
from ingestion import build_clean_dataframe, write_clean_artifacts,fetch_source_records, load_raw_records
from observability import build_freshness_report, run_data_quality_checks, generate_phase1_report
from retrieval import validate_clean_dataframe, LocalEmbeddingIndex
from evaluation import evaluate_pipeline, build_test_set, verify_test_set_against_index

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Xây dựng và thực thi Phase 1 Baseline Pipeline End-to-End:

    1. Load configuration settings & khởi tạo thư mục dự án.
    2. Load hoặc fetch raw Crossref records.
    3. Clean data & ghi nhận file artifacts (CSV, JSON, Audit Report).
    4. Validate clean dataframe schema cho Retrieval Contract.
    5. Khởi tạo & xây dựng Local Embedding Index (Chroma Vector Store).
    6. Chạy bộ Data Quality Checks & Freshness Report.
    7. Tạo mới hoặc nạp Evaluation Test Set & xác minh với Vector Index.
    8. Thực thi đánh giá tự động (Retrieval Hit Rate, Token F1, LLM Judge Score).
    9. Tổng hợp dữ liệu thực tế và xuất báo cáo Markdown Phase 1.
    """
    logger.info("==================================================")
    logger.info("  BẮT ĐẦU CHẠY BASELINE PIPELINE FULL (PHASE 1)   ")
    logger.info("==================================================")

    # -------------------------------------------------------------------------
    # STEP 1: LOAD SETTINGS & SETUP DIRECTORIES
    # -------------------------------------------------------------------------
    logger.info("[Step 1/8] Loading settings & initializing directories...")
    settings = load_settings()

    # Đảm bảo tất cả các thư mục lưu trữ artifact đều tồn tại
    output_directories = (
        settings.paths.quality_dir,
        settings.paths.chroma_dir,
        settings.paths.clean_csv.parent,
        settings.paths.eval_testset.parent,
        settings.paths.baseline_metrics.parent,
        settings.paths.baseline_report.parent,
    )
    for path in output_directories:
        path.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # STEP 2: INGESTION - FETCH OR LOAD RAW RECORDS
    # -------------------------------------------------------------------------
    logger.info("[Step 2/8] Fetching / Loading raw Crossref records...")
    raw_snapshot_path = settings.paths.raw_records_json

    if raw_snapshot_path.exists() and not settings.refresh_source:
        logger.info(f"Phát hiện raw snapshot tại '{raw_snapshot_path}'. Tiến hành load...")
        records = load_raw_records(raw_snapshot_path)
    else:
        logger.info("Chưa có raw snapshot hoặc `refresh_source=True`. Đang gọi Crossref API...")
        records = fetch_source_records(settings)

    logger.info(f"-> Thu thập thành công {len(records)} raw records.")

    # -------------------------------------------------------------------------
    # STEP 3: CLEAN DATA & WRITE ARTIFACTS
    # -------------------------------------------------------------------------
    logger.info("[Step 3/8] Cleaning raw data & writing clean artifacts...")
    run_date = datetime.now()
    df_clean = build_clean_dataframe(records, run_date=run_date)

    cleaning_report_path = settings.paths.quality_dir / "cleaning_report.json"
    cleaning_report = write_clean_artifacts(
        df=df_clean,
        csv_path=settings.paths.clean_csv,
        json_path=settings.paths.clean_json,
        report_path=cleaning_report_path,
    )

    logger.info(f"-> Dataframe làm sạch: giữ lại {len(df_clean)} / {len(records)} bản ghi.")
    logger.info(f"-> Báo cáo Audit Trail đã lưu tại: '{cleaning_report_path}'")

    # Đọc lại từ CSV đã ghi, vì test set cũng được build từ chính file CSV này.
    # Nếu build index thẳng từ dataframe in-memory, `published` còn là Timestamp và render
    # thành "...T00:00:00+00:00" thay vì "... 00:00:00+00:00" như trong ground truth
    # -> 6 câu hỏi loại `date` có token_f1 = 0 vì định dạng, không phải vì chất lượng dữ liệu.
    df_clean = pd.read_csv(settings.paths.clean_csv)

    if df_clean.empty:
        raise RuntimeError("[BLOCKER] Clean dataframe bị rỗng! Không thể tiếp tục pipeline.")

    # Validate Handoff Contract
    logger.info("Validating clean dataframe schema for Retrieval Contract...")
    contract_check = validate_clean_dataframe(df_clean)
    if contract_check["status"] == "fail":
        raise RuntimeError(f"[BLOCKER] Clean dataframe không đạt Retrieval Contract: {contract_check}")

    if contract_check.get("warnings"):
        for warning in contract_check["warnings"]:
            logger.warning(f"  [CONTRACT WARNING] {warning}")

    logger.info("-> Clean Dataframe đạt yêu cầu Retrieval Contract 100%.")

    # -------------------------------------------------------------------------
    # STEP 4: BUILD EMBEDDING INDEX (CHROMA VECTOR STORE)
    # -------------------------------------------------------------------------
    logger.info("[Step 4/8] Building Local Embedding Index (Chroma Vector Store)...")
    logger.info(f"  Model: {settings.embedding_model}")
    logger.info(f"  Collection Name: {settings.baseline_collection_name}")

    index = LocalEmbeddingIndex.build(
        df=df_clean,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    logger.info(f"-> Tạo Embedding Index thành công với {len(index.documents)} documents.")

    # -------------------------------------------------------------------------
    # STEP 5: RUN DATA QUALITY CHECKS & FRESHNESS REPORT
    # -------------------------------------------------------------------------
    logger.info("[Step 5/8] Running Data Quality Checks & Freshness Report...")
    quality_payload = run_data_quality_checks(
        df=df_clean,
        settings=settings,
        report_name="phase1_baseline",
    )
    logger.info(f"-> Quality Check: Passed {quality_payload['passed']}/{len(quality_payload['checks'])} checks.")

    freshness_payload = build_freshness_report(
        df=df_clean,
        settings=settings,
        report_path=settings.paths.freshness_report,
    )
    logger.info(f"-> Freshness Report đã lưu tại '{settings.paths.freshness_report}' (is_fresh={freshness_payload['is_fresh']})")

    # -------------------------------------------------------------------------
    # STEP 6: CREATE OR LOAD EVALUATION TEST SET
    # -------------------------------------------------------------------------
    logger.info("[Step 6/8] Handling Evaluation Test Set...")
    test_set_path = settings.paths.eval_testset

    if test_set_path.exists() and not settings.refresh_test_set:
        logger.info(f"Phát hiện test set có sẵn tại: '{test_set_path}'. Đang load...")
    else:
        logger.info(f"Tạo mới test set từ clean dataframe và ghi ra: '{test_set_path}'...")
        build_test_set(df_clean, output_path=test_set_path)

    # Xác minh tính khớp giữa Test Set và Vector Index
    test_set_data = read_json(test_set_path)
    verify_res = verify_test_set_against_index(test_set_data, index)
    if not verify_res["success"]:
        logger.warning(f"Cảnh báo lệch match giữa Test Set và Index: {verify_res}")
    else:
        logger.info(f"-> Verify Test Set vs Index thành công! Tổng số câu hỏi: {verify_res['samples']}")

    # -------------------------------------------------------------------------
    # STEP 7: EVALUATE PIPELINE
    # -------------------------------------------------------------------------
    logger.info("[Step 7/8] Running Pipeline Evaluation Pass...")
    eval_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=test_set_path,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    metrics_summary = eval_bundle.summary
    logger.info("-> Kết quả Evaluation Metrics:")
    logger.info(f"   - Retrieval Hit Rate: {metrics_summary.get('retrieval_hit_rate', 0.0):.4f}")
    logger.info(f"   - Mean Token F1:     {metrics_summary.get('mean_token_f1', 0.0):.4f}")
    logger.info(f"   - Judge Accuracy:    {metrics_summary.get('judge_accuracy', 0.0):.4f}")

    # -------------------------------------------------------------------------
    # STEP 8: GENERATE MARKDOWN BASELINE REPORT
    # -------------------------------------------------------------------------
    logger.info("[Step 8/8] Generating Markdown Report...")
    source_summary = {
        "source": settings.source_api,
        "query": settings.source_query,
        "raw_records": len(records),
        "clean_records": len(df_clean),
        "freshness_threshold_days": settings.freshness_threshold_days,
    }

    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=metrics_summary,
        quality=quality_payload,
        freshness=freshness_payload,
    )
    logger.info(f"-> Báo cáo Markdown Baseline hoàn tất tại: '{settings.paths.baseline_report}'")

    logger.info("==================================================")
    logger.info(" PIPELINE PHASE 1 ĐÃ CHẠY HOÀN THÀNH THÀNH CÔNG! ")
    logger.info("==================================================")

if __name__ == "__main__":
    main()