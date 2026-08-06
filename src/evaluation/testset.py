from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, write_json

MIN_PAPERS = 6

REQUIRED_FIELDS = ("paper_id", "title", "summary", "authors_joined", "categories_joined", "published")

REQUIRED_SAMPLE_KEYS = ("id", "question_type", "question", "ground_truth", "ground_truth_doc_ids")

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
        return "title_contains_single_quote"
    if re.search(r"<[^>]+>", title):
        return "title_contains_markup"
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


def validate_test_set(test_set: list[dict[str, Any]], df: pd.DataFrame) -> list[str]:
    """Tra ve list loi. Rong nghia la test set dung contract cua `metrics.evaluate_pipeline`."""
    errors: list[str] = []
    known_ids = set(df["paper_id"].astype(str)) if "paper_id" in df.columns else set()
    seen_ids: set[str] = set()

    for item in test_set:
        missing_keys = [key for key in REQUIRED_SAMPLE_KEYS if key not in item]
        if missing_keys:
            errors.append(f"{item.get('id', '<no id>')}: thieu key {missing_keys}")
            continue
        if item["id"] in seen_ids:
            errors.append(f"{item['id']}: id bi trung")
        seen_ids.add(item["id"])
        if not str(item["question"]).strip():
            errors.append(f"{item['id']}: question rong")
        if not str(item["ground_truth"]).strip():
            errors.append(f"{item['id']}: ground_truth rong")
        if not item["ground_truth_doc_ids"]:
            errors.append(f"{item['id']}: ground_truth_doc_ids rong")
        for doc_id in item["ground_truth_doc_ids"]:
            if known_ids and doc_id not in known_ids:
                errors.append(f"{item['id']}: doc_id `{doc_id}` khong co trong cleaned dataframe")

    return errors


def verify_test_set_against_index(test_set: list[dict[str, Any]], index) -> dict[str, Any]:
    """Kiem tra moi `ground_truth_doc_ids` va title trong cau hoi deu lookup duoc trong index.

    Miss o day la loi contract giua clean va index -> sua contract, khong sua test set cho khop.
    """
    missing_doc_ids: list[str] = []
    missing_titles: list[str] = []

    for item in test_set:
        for doc_id in item["ground_truth_doc_ids"]:
            if index.lookup(doc_id) is None and doc_id not in missing_doc_ids:
                missing_doc_ids.append(doc_id)
        title_match = re.search(r"'([^']+)'", item["question"])
        if title_match:
            title = title_match.group(1)
            if index.lookup(title) is None and title not in missing_titles:
                missing_titles.append(title)

    return {
        "samples": len(test_set),
        "unique_doc_ids": len({doc_id for item in test_set for doc_id in item["ground_truth_doc_ids"]}),
        "missing_doc_ids": missing_doc_ids,
        "missing_titles": missing_titles,
        "success": not missing_doc_ids and not missing_titles,
    }


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Tao evaluation set tu cleaned dataframe va ghi JSON ra `output_path`.

    Test set duoc khoa lai: baseline, corrupted va repaired deu dung dung file nay,
    neu sinh lai giua chung thi so sanh ba trang thai mat cong bang.
    """
    selected, rejected = select_representative_papers(df)
    if len(selected) < MIN_PAPERS:
        reasons = ", ".join(sorted({item["reason"] for item in rejected})) or "khong ro"
        raise ValueError(
            f"Chi chon duoc {len(selected)}/{MIN_PAPERS} paper hop le tu {len(df)} row clean. "
            f"Ly do loai: {reasons}. Sua data contract truoc, dung ha tieu chuan test set."
        )

    test_set = [sample for row in selected for sample in draft_questions(row)]

    errors = validate_test_set(test_set, df)
    if errors:
        raise ValueError("Test set khong hop le:\n- " + "\n- ".join(errors))

    write_json(Path(output_path), test_set)
    return test_set
