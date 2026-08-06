from datetime import UTC, datetime
from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "script"))

from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import PaperRecord
from run_repair_cp6 import infer_baseline_run_date


class RepairTest(unittest.TestCase):
    def test_infers_original_run_date_for_reproducible_repair(self) -> None:
        records = [
            PaperRecord(
                paper_id=f"paper-{index}", title=f"Title {index}", summary="Long clean summary",
                authors=["Author"], categories=["RAG"], primary_category="RAG",
                published=f"2026-08-0{index + 1}", updated="2026-08-05",
                abs_url="", pdf_url="", comment="",
            )
            for index in range(3)
        ]
        baseline = build_clean_dataframe(records, datetime(2026, 8, 6, tzinfo=UTC))

        inferred = infer_baseline_run_date(baseline)

        self.assertEqual(inferred, datetime(2026, 8, 6, tzinfo=UTC))
        repaired = build_clean_dataframe(records, inferred)
        pd.testing.assert_series_equal(baseline["age_days"], repaired["age_days"])


if __name__ == "__main__":
    unittest.main()
