from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
import json
import sys

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "src"))

from core.config import load_settings
from core.utils import read_json, write_json, write_text
from ingestion.cleaning import CLEAN_COLUMNS, build_clean_dataframe, write_clean_artifacts
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from retrieval.contract import validate_clean_dataframe


def infer_baseline_run_date(baseline: pd.DataFrame) -> datetime:
    """Recover the original cleaning run date from published + age_days."""
    published = pd.to_datetime(baseline["published"], errors="coerce", utc=True, format="mixed")
    ages = pd.to_numeric(baseline["age_days"], errors="coerce")
    candidates = (published.dt.normalize() + pd.to_timedelta(ages, unit="D")).dropna()
    if candidates.empty:
        raise ValueError("Cannot infer baseline run date from published and age_days.")
    counts = Counter(value.date() for value in candidates)
    run_day, occurrences = counts.most_common(1)[0]
    if occurrences != len(candidates):
        raise ValueError(f"Baseline age_days is inconsistent; inferred run dates: {dict(counts)}")
    return datetime(run_day.year, run_day.month, run_day.day, tzinfo=UTC)


def compare_repair(
    baseline: pd.DataFrame,
    corrupted: pd.DataFrame,
    repaired: pd.DataFrame,
    corruption_log: dict,
) -> dict:
    baseline_by_id = {str(row["paper_id"]): row for row in baseline.to_dict(orient="records")}
    repaired_by_id = {str(row["paper_id"]): row for row in repaired.to_dict(orient="records")}
    operations = {item["type"]: item for item in corruption_log["operations"]}

    dropped_ids = operations["drop_latest"]["record_ids"]
    missing_id = operations["missing_summary"]["record_ids"][0]
    noise_id = operations["inject_noise"]["record_ids"][0]
    old_date_id = operations["old_published_date"]["record_ids"][0]
    duplicate_id = operations["add_duplicate"]["record_ids"][0]
    marker = operations["inject_noise"]["parameter"]["marker"]

    checks = {
        "schema_matches_baseline": list(repaired.columns) == list(baseline.columns) == CLEAN_COLUMNS,
        "row_count_restored": len(repaired) == len(baseline),
        "paper_ids_restored": set(repaired_by_id) == set(baseline_by_id),
        "dropped_records_restored": all(paper_id in repaired_by_id for paper_id in dropped_ids),
        "missing_summary_restored": str(repaired_by_id[missing_id]["summary"]).strip() != "",
        "noise_removed": marker not in str(repaired_by_id[noise_id]["text_for_embedding"]),
        "old_date_restored": pd.to_datetime(
            repaired_by_id[old_date_id]["published"], errors="coerce", utc=True
        )
        == pd.to_datetime(baseline_by_id[old_date_id]["published"], errors="coerce", utc=True),
        "duplicate_removed": int((repaired["paper_id"].astype(str) == duplicate_id).sum()) == 1,
        "repaired_ids_unique": repaired["paper_id"].astype(str).is_unique,
        "repaired_embeddings_nonempty": repaired["text_for_embedding"].astype(str).str.strip().ne("").all(),
        "corrupted_differs_from_baseline": baseline.to_json(orient="records", date_format="iso")
        != corrupted.to_json(orient="records", date_format="iso"),
    }
    return {
        "baseline_rows": len(baseline),
        "corrupted_rows": len(corrupted),
        "repaired_rows": len(repaired),
        "checks": {key: bool(value) for key, value in checks.items()},
        "success": all(checks.values()),
    }


def render_report(validation: dict, quality: dict, freshness: dict, run_date: datetime) -> str:
    lines = [
        "# Vai trò 3 — CP6 Repair từ raw",
        "",
        f"- Baseline cleaning run date: `{run_date.date().isoformat()}`",
        f"- Baseline rows: **{validation['baseline_rows']}**",
        f"- Corrupted rows: **{validation['corrupted_rows']}**",
        f"- Repaired rows: **{validation['repaired_rows']}**",
        f"- Repair status: **{'PASS' if validation['success'] else 'FAIL'}**",
        f"- Quality: **{quality['passed']}/{len(quality['checks'])} checks pass**",
        f"- Freshness: **{'PASS' if freshness['is_fresh'] else 'FAIL'}**",
        "",
        "## Baseline / corrupted / repaired",
        "",
        "| Kiểm tra | Kết quả |",
        "| --- | --- |",
    ]
    for name, success in validation["checks"].items():
        lines.append(f"| `{name}` | {'PASS' if success else '**FAIL**'} |")
    lines += [
        "",
        "Repaired dataset được tạo bằng cách nạp lại `data/raw/crossref_records.json` "
        "và gọi `build_clean_dataframe`; không copy hoặc sửa tay baseline/corrupted artifact.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    settings = load_settings(PROJECT_DIR)
    baseline = pd.read_json(settings.paths.clean_json)
    corrupted = pd.read_json(settings.paths.corrupted_clean_json)
    corruption_log = read_json(settings.paths.corruption_log)
    raw_records = load_raw_records(settings.paths.raw_records_json)

    run_date = infer_baseline_run_date(baseline)
    repaired = build_clean_dataframe(raw_records, run_date=run_date)
    contract = validate_clean_dataframe(repaired)
    if contract["status"] != "pass":
        raise RuntimeError(f"Repaired clean contract failed: {contract}")

    cleaning_report_path = settings.paths.quality_dir / "repaired_cleaning_report.json"
    write_clean_artifacts(
        repaired,
        settings.paths.repaired_clean_csv,
        settings.paths.repaired_clean_json,
        cleaning_report_path,
    )
    quality = run_data_quality_checks(repaired, settings, report_name="repaired")
    freshness_path = settings.paths.quality_dir / "repaired_freshness_report.json"
    freshness = build_freshness_report(repaired, settings, freshness_path)

    validation = compare_repair(baseline, corrupted, repaired, corruption_log)
    validation.update(
        {
            "source": str(settings.paths.raw_records_json.relative_to(PROJECT_DIR)),
            "run_date": run_date.date().isoformat(),
            "contract_status": contract["status"],
            "quality_success": quality["success"],
            "freshness_success": freshness["is_fresh"],
        }
    )
    validation["success"] = bool(
        validation["success"] and quality["success"] and freshness["is_fresh"]
    )
    validation_path = settings.paths.results_dir / "repair_validation.json" if hasattr(settings.paths, "results_dir") else settings.paths.repaired_metrics.parent / "repair_validation.json"
    write_json(validation_path, validation)

    report_path = settings.paths.comparison_report.parent / "role3_cp6_repair_report.md"
    write_text(report_path, render_report(validation, quality, freshness, run_date))
    print(f"Repaired rows: {len(repaired)} from {len(raw_records)} raw records")
    print(f"Quality: {quality['passed']}/{len(quality['checks'])}; freshness={freshness['is_fresh']}")
    print(f"Validation: {validation_path}")
    print(f"Report: {report_path}")
    if not validation["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
