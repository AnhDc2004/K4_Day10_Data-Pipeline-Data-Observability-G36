from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from retrieval.contract import build_document_preview, validate_clean_dataframe
from retrieval.index import LocalEmbeddingIndex


class RetrievalContractTest(unittest.TestCase):
    def test_valid_clean_dataframe_maps_to_index_document(self) -> None:
        frame = pd.DataFrame(
            [
                {
                    "paper_id": "10.1000/example",
                    "title": "Example paper",
                    "summary": "A summary.",
                    "authors_joined": "A. Author",
                    "categories_joined": "Machine Learning",
                    "published": "2026-01-01T00:00:00Z",
                    "abs_url": "https://doi.org/10.1000/example",
                    "pdf_url": "",
                    "text_for_embedding": "Title: Example paper\nSummary: A summary.",
                }
            ]
        )

        result = validate_clean_dataframe(frame)

        self.assertEqual(result["status"], "pass")
        document = build_document_preview(frame.iloc[0], 0)
        self.assertEqual(document["record_id"], "10.1000/example::0")
        self.assertEqual(document["content"], frame.iloc[0]["text_for_embedding"])
        self.assertEqual(document["metadata"]["paper_id"], "10.1000/example")

    def test_duplicate_id_and_empty_embedding_fail(self) -> None:
        frame = pd.DataFrame(
            [
                {"paper_id": "same", "title": "One", "summary": "", "authors_joined": "", "categories_joined": "", "published": "", "abs_url": "", "pdf_url": "", "text_for_embedding": "Title: One"},
                {"paper_id": "same", "title": "Two", "summary": "", "authors_joined": "", "categories_joined": "", "published": "", "abs_url": "", "pdf_url": "", "text_for_embedding": ""},
            ]
        )

        result = validate_clean_dataframe(frame)

        self.assertEqual(result["status"], "fail")
        self.assertIn("duplicate_paper_ids", result["hard_failures"])
        self.assertEqual(result["empty_fields"]["text_for_embedding"], 1)

    def test_index_metadata_serializes_pandas_timestamp_for_chroma(self) -> None:
        frame = pd.DataFrame(
            [
                {
                    "paper_id": "10.1000/date",
                    "title": "Timestamp paper",
                    "summary": "A summary.",
                    "authors_joined": "A. Author",
                    "categories_joined": "RAG",
                    "published": pd.Timestamp("2026-08-01", tz="UTC"),
                    "abs_url": "https://doi.org/10.1000/date",
                    "pdf_url": float("nan"),
                    "text_for_embedding": "Title: Timestamp paper\nSummary: A summary.",
                }
            ]
        )

        document = LocalEmbeddingIndex._build_documents(frame)[0]

        self.assertEqual(document["metadata"]["published"], "2026-08-01T00:00:00+00:00")
        self.assertEqual(document["metadata"]["pdf_url"], "")


if __name__ == "__main__":
    unittest.main()
