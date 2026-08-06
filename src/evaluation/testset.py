from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace

MIN_PAPERS = 6

REQUIRED_FIELDS = ("paper_id", "title", "summary", "authors_joined", "categories_joined", "published")

# Cum tu khoa phai giu nguyen: `retrieval/qa.py::_extract_answer` route answer bang cach
# match chuoi tren question.lower(). Doi cach dien dat -> answer roi ve nhanh summary mac dinh.
QUESTION_TEMPLATES: dict[str, str] = {
    "summary": "What is the paper '{title}' about?",
    "authors": "Who authored the paper '{title}'?",
    "date": "When was the paper '{title}' published?",
    "categories": "What categories does the paper '{title}' belong to?",
}


def _text(row: dict[str, Any], column: str) -> str:
    value = row.get(column)
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return normalize_whitespace(str(value))


def paper_rejection_reason(row: dict[str, Any]) -> str | None:
    """Ly do mot paper khong dung lam evaluation sample. Tra ve None neu dung duoc."""
    for field in REQUIRED_FIELDS:
        if not _text(row, field):
            return f"missing_{field}"
    title = _text(row, "title")
    if "'" in title:
        # `qa.answer_question` bat exact title bang regex r"'([^']+)'" -> title co nhay don lam vo lookup.
        return "title_contains_single_quote"
    if len(title) < 10:
        return "title_too_short"
    if len(_text(row, "summary")) < 100:
        return "summary_too_short"
    return None


def select_representative_papers(
    df: pd.DataFrame,
    limit: int = MIN_PAPERS,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Chon paper dai dien tu cleaned dataframe, kem log ly do loai tung row.

    Uu tien paper moi nhat va da dang `primary_category`; loai title trung/giong prefix
    de exact lookup theo title khong bi mo ho.
    """
    if "paper_id" not in df.columns or "title" not in df.columns:
        raise ValueError("Cleaned dataframe phai co cot `paper_id` va `title` truoc khi build test set.")

    working = df.copy()
    if "age_days" in working.columns:
        working = working.sort_values("age_days", ascending=True, kind="stable")

    selected: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    used_categories: set[str] = set()
    used_title_prefixes: set[str] = set()

    records = working.to_dict(orient="records")
    # pass 0: moi category chi lay 1 paper (da dang hon); pass 1: lay them cho du limit.
    for prefer_new_category in (True, False):
        for row in records:
            if len(selected) >= limit:
                break
            paper_id = _text(row, "paper_id")
            if any(item["paper_id"] == paper_id for item in selected):
                continue

            reason = paper_rejection_reason(row)
            if not reason and _text(row, "title").lower()[:40] in used_title_prefixes:
                reason = "title_prefix_duplicate"
            if reason:
                if not any(item["paper_id"] == paper_id for item in rejected):
                    rejected.append({"paper_id": paper_id, "title": _text(row, "title"), "reason": reason})
                continue

            category = _text(row, "primary_category") or _text(row, "categories_joined")
            if prefer_new_category and category in used_categories:
                continue

            selected.append(row)
            used_categories.add(category)
            used_title_prefixes.add(_text(row, "title").lower()[:40])

    return selected, rejected


def draft_questions(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Sinh 4 sample (summary/authors/date/categories) cho mot paper.

    `ground_truth` copy nguyen van gia tri cot nguon vi `_extract_answer` tra ve chinh
    gia tri metadata do; `ground_truth_doc_ids` lay tu `paper_id` cua chinh row nay.
    """
    paper_id = _text(row, "paper_id")
    title = _text(row, "title")
    ground_truths = {
        "summary": first_sentence(_text(row, "summary")),
        "authors": _text(row, "authors_joined"),
        "date": _text(row, "published"),
        "categories": _text(row, "categories_joined"),
    }
    return [
        {
            "id": f"{paper_id}::{question_type}",
            "question_type": question_type,
            "question": template.format(title=title),
            "ground_truth": ground_truths[question_type],
            "ground_truth_doc_ids": [paper_id],
        }
        for question_type, template in QUESTION_TEMPLATES.items()
    ]


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """TODO(CP2): compose `select_representative_papers` + `draft_questions`, validate va write_json.

    Chua ghi file o CP1: `paper_id` phai on dinh va moi id phai lookup duoc trong index
    truoc khi khoa test set lai cho ca ba trang thai baseline/corrupted/repaired.
    """
    raise NotImplementedError("CP2 task: write locked test set after paper_id is stable.")
