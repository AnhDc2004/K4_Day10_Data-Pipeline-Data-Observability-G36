from datetime import UTC, datetime
from pathlib import Path
import sys
import unittest

import pandas as pd

# Allow the CP1 sample to run before the project is installed as a package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingestion.cleaning import CLEAN_COLUMNS, build_clean_dataframe, write_clean_artifacts
from ingestion.crossref import PaperRecord


def paper(**overrides) -> PaperRecord:
    values = {
        "paper_id": "10.1000/sample",
        "title": "  A   useful paper  ",
        "summary": "  A summary with   extra spaces. ",
        "authors": [" Alice ", "Bob", "alice", ""],
        "categories": ["AI", " Data ", "ai"],
        "primary_category": "ML",
        "published": "2026-01-01T10:00:00Z",
        "updated": "2026-01-02T10:00:00Z",
        "abs_url": " https://example.test/abs ",
        "pdf_url": "https://example.test/pdf",
        "comment": " sample ",
    }
    values.update(overrides)
    return PaperRecord(**values)


class CleanDataframeTest(unittest.TestCase):
    def test_raw_to_clean_sample_contract(self) -> None:
        df = build_clean_dataframe([paper()], datetime(2026, 1, 11, tzinfo=UTC))

        self.assertEqual(list(df.columns), CLEAN_COLUMNS)
        self.assertEqual(len(df), 1)
        row = df.iloc[0]
        self.assertEqual(row["title"], "A useful paper")
        self.assertEqual(row["summary"], "A summary with extra spaces.")
        self.assertEqual(row["authors"], ["Alice", "Bob"])
        self.assertEqual(row["categories"], ["ML", "AI", "Data"])
        self.assertEqual(row["authors_joined"], "Alice, Bob")
        self.assertEqual(row["categories_joined"], "ML, AI, Data")
        self.assertEqual(row["summary_chars"], len(row["summary"]))
        self.assertEqual(row["age_days"], 10)
        self.assertEqual(
            row["text_for_embedding"],
            "Title: A useful paper\n"
            "Summary: A summary with extra spaces.\n"
            "Authors: Alice, Bob\n"
            "Categories: ML, AI, Data",
        )

    def test_invalid_required_fields_removed_and_optional_nulls_retained(self) -> None:
        valid = paper(summary=None, authors=None, categories=None, published="not-a-date", updated="")
        df = build_clean_dataframe(
            [valid, paper(paper_id=""), paper(paper_id="other", title="   ")],
            datetime(2026, 1, 11),
        )

        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["summary"], "")
        self.assertTrue(pd.isna(df.iloc[0]["published"]))
        self.assertTrue(pd.isna(df.iloc[0]["age_days"]))
        self.assertTrue(df.iloc[0]["text_for_embedding"].startswith("Title:"))

    def test_duplicate_id_keeps_latest_update_and_future_date_has_zero_age(self) -> None:
        old = paper(title="Old title", updated="2026-01-01", published="2026-02-01")
        new = paper(title="New title", updated="2026-01-03", published="2026-02-01")

        df = build_clean_dataframe([new, old], datetime(2026, 1, 11, tzinfo=UTC))

        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["title"], "New title")
        self.assertEqual(df.iloc[0]["age_days"], 0)
        self.assertEqual(df.attrs["cleaning_report"]["duplicates_removed"], 1)

    def test_writes_clean_artifacts_and_reason_counts(self) -> None:
        from tempfile import TemporaryDirectory

        records = [paper(), paper(), paper(paper_id=""), paper(paper_id="other", title="")]
        df = build_clean_dataframe(records, datetime(2026, 1, 11, tzinfo=UTC))

        with TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            report = write_clean_artifacts(
                df,
                target / "papers.csv",
                target / "papers.json",
                target / "cleaning_report.json",
            )
            self.assertTrue((target / "papers.csv").is_file())
            self.assertTrue((target / "papers.json").is_file())
            self.assertTrue((target / "cleaning_report.json").is_file())

        self.assertEqual(report["input_records"], 4)
        self.assertEqual(report["dropped_missing_paper_id"], 1)
        self.assertEqual(report["dropped_missing_title"], 1)
        self.assertEqual(report["filtered_records"], 2)
        self.assertEqual(report["duplicates_removed"], 1)
        self.assertEqual(report["output_records"], 1)


if __name__ == "__main__":
    unittest.main()
