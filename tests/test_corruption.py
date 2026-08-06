from pathlib import Path
import json
import sys
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingestion.corruption import NOISE_MARKER, corrupt_clean_dataframe


class CorruptionTest(unittest.TestCase):
    def baseline(self) -> pd.DataFrame:
        rows = []
        for index in range(8):
            rows.append(
                {
                    "paper_id": f"paper-{index}",
                    "title": f"Title {index}",
                    "summary": f"Summary {index}",
                    "authors_joined": "Author",
                    "categories_joined": "RAG",
                    "published": pd.Timestamp("2026-08-01", tz="UTC") - pd.Timedelta(days=index),
                    "age_days": index + 5,
                    "summary_chars": len(f"Summary {index}"),
                    "text_for_embedding": f"Title: Title {index}\nSummary: Summary {index}",
                }
            )
        return pd.DataFrame(rows)

    def test_all_corruptions_and_log_match_dataset(self) -> None:
        baseline = self.baseline()
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "corruption_log.json"
            corrupted = corrupt_clean_dataframe(baseline, log_path)
            log = json.loads(log_path.read_text(encoding="utf-8"))

        self.assertEqual(len(baseline), 8)  # input was not mutated
        self.assertEqual(len(corrupted), 7)  # drop 2, duplicate 1
        self.assertEqual(log["baseline_count"], 8)
        self.assertEqual(log["corrupted_count"], 7)
        self.assertEqual(
            [item["type"] for item in log["operations"]],
            ["drop_latest", "missing_summary", "inject_noise", "old_published_date", "add_duplicate"],
        )
        for item in log["operations"]:
            self.assertTrue(item["record_ids"])
            self.assertIsInstance(item["parameter"], dict)
            self.assertIn("before_count", item)
            self.assertIn("after_count", item)

        dropped = set(log["operations"][0]["record_ids"])
        self.assertTrue(dropped.isdisjoint(set(corrupted["paper_id"])))

        missing_id = log["operations"][1]["record_ids"][0]
        self.assertEqual(corrupted.loc[corrupted.paper_id == missing_id, "summary"].iloc[0], "")

        noisy_id = log["operations"][2]["record_ids"][0]
        noisy = corrupted.loc[corrupted.paper_id == noisy_id].iloc[0]
        self.assertIn(NOISE_MARKER, noisy["summary"])
        self.assertIn(NOISE_MARKER, noisy["text_for_embedding"])

        old_id = log["operations"][3]["record_ids"][0]
        old = corrupted.loc[corrupted.paper_id == old_id].iloc[0]
        original = baseline.loc[baseline.paper_id == old_id].iloc[0]
        self.assertEqual(old["age_days"], original["age_days"] + 730)

        duplicate_id = log["operations"][4]["record_ids"][0]
        self.assertEqual(int((corrupted.paper_id == duplicate_id).sum()), 2)
        self.assertTrue(corrupted["text_for_embedding"].str.strip().ne("").all())


if __name__ == "__main__":
    unittest.main()
