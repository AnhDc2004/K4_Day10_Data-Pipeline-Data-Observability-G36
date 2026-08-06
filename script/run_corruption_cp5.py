from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "src"))

from core.config import load_settings
from core.utils import write_csv, write_json
from ingestion.corruption import corrupt_clean_dataframe


def main() -> None:
    settings = load_settings(PROJECT_DIR)
    baseline = pd.read_json(settings.paths.clean_json)
    corrupted = corrupt_clean_dataframe(baseline, settings.paths.corruption_log)

    write_csv(corrupted, settings.paths.corrupted_clean_csv)
    json_records = json.loads(corrupted.to_json(orient="records", date_format="iso"))
    write_json(settings.paths.corrupted_clean_json, json_records)

    print(f"Baseline rows: {len(baseline)}")
    print(f"Corrupted rows: {len(corrupted)}")
    print(f"Corruption log: {settings.paths.corruption_log}")


if __name__ == "__main__":
    main()
