from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "src"))

from core.config import load_settings
from core.utils import read_json
from ingestion.cleaning import build_clean_dataframe, write_clean_artifacts
from ingestion.crossref import PaperRecord


def main() -> None:
    settings = load_settings(PROJECT_DIR)
    payload = read_json(settings.paths.raw_records_json)
    if not isinstance(payload, list):
        raise ValueError(f"Expected a JSON list in {settings.paths.raw_records_json}")

    records = [PaperRecord(**item) for item in payload]
    clean_df = build_clean_dataframe(records, datetime.now(UTC))
    report_path = settings.paths.clean_csv.parent / "cleaning_report.json"
    report = write_clean_artifacts(
        clean_df,
        settings.paths.clean_csv,
        settings.paths.clean_json,
        report_path,
    )
    print(f"Wrote {report['output_records']} clean records to {settings.paths.clean_csv}")
    print(f"Cleaning report: {report_path}")


if __name__ == "__main__":
    main()
