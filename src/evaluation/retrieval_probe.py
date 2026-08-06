"""Test set phu de do rieng tang retrieval.

Test set chinh (`data/eval/test_set.json`) nhung cau hoi deu chua nguyen title trong dau nhay don,
nen `qa.answer_question` bat duoc bang exact lookup va retrieval gan nhu khong the sai.
Probe set nay co y **khong** chua title: cau hoi duoc dien dat lai tu noi dung paper, buoc semantic
search phai lam viec that. Dung de phan tich, **khong thay the** test set chinh da khoa.

Metric o day la retrieval thuan (hit@k, MRR, top1) nen khong ton mot lan goi LLM nao luc evaluate;
LLM chi duoc dung mot lan duy nhat luc sinh cau hoi, sau do ket qua duoc khoa vao file.
"""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

from core.config import Settings
from core.utils import normalize_whitespace, write_json
from retrieval.llm import build_llm

QUESTIONS_PER_PAPER = 2
MAX_TITLE_NGRAM = 4  # cau hoi khong duoc lap >= 4 tu lien tiep cua title


class ProbeQuestions(BaseModel):
    questions: list[str] = Field(min_length=1, max_length=4)


def _title_ngrams(title: str, size: int = MAX_TITLE_NGRAM) -> set[str]:
    words = [word for word in re.findall(r"[a-z0-9]+", title.lower()) if word]
    return {" ".join(words[i : i + size]) for i in range(max(0, len(words) - size + 1))}


def question_rejection_reason(question: str, title: str) -> str | None:
    """Cau hoi probe khong duoc muon title, vi nhu vay la quay lai exact lookup."""
    text = normalize_whitespace(question)
    if len(text) < 25:
        return "too_short"
    if "'" in text:
        # `qa.answer_question` coi chuoi trong nhay don la khoa exact lookup.
        return "contains_single_quote"
    lowered = " ".join(re.findall(r"[a-z0-9]+", text.lower()))
    if any(ngram in lowered for ngram in _title_ngrams(title)):
        return "repeats_title_ngram"
    return None


def _prompt(title: str, summary: str) -> str:
    return f"""
Write {QUESTIONS_PER_PAPER} short English questions that a researcher would ask to FIND this paper.

Paper abstract: {summary[:1200]}

Hard rules:
- Describe the method, problem or contribution in your own words.
- NEVER quote or paraphrase the paper title, and never use apostrophes.
- Each question must be answerable only by this paper, not by any paper on the same broad topic.
- One sentence each, under 25 words.
""".strip()


def build_probe_set(
    df: pd.DataFrame,
    settings: Settings,
    output_path: Path,
    paper_ids: list[str],
) -> list[dict[str, Any]]:
    """Sinh probe questions bang LLM cho cac paper chi dinh va ghi ra JSON.

    Chi chay mot lan; file ghi ra duoc khoa lai va dung chung cho baseline/corrupted/repaired.
    """
    llm = build_llm(settings=settings, temperature=0.3).with_structured_output(ProbeQuestions)
    rows = {str(record["paper_id"]): record for record in df.to_dict(orient="records")}

    probe_set: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []

    for paper_id in paper_ids:
        row = rows.get(paper_id)
        if row is None:
            rejected.append({"paper_id": paper_id, "reason": "paper_id_not_in_clean"})
            continue
        title = normalize_whitespace(str(row["title"]))
        verdict = llm.invoke(_prompt(title, normalize_whitespace(str(row["summary"]))))
        for order, question in enumerate(verdict.questions[:QUESTIONS_PER_PAPER]):
            reason = question_rejection_reason(question, title)
            if reason:
                rejected.append({"paper_id": paper_id, "question": question, "reason": reason})
                continue
            probe_set.append(
                {
                    "id": f"{paper_id}::probe{order}",
                    "question_type": "retrieval_probe",
                    "question": normalize_whitespace(question),
                    "ground_truth": normalize_whitespace(str(row["title"])),
                    "ground_truth_doc_ids": [paper_id],
                }
            )

    write_json(Path(output_path), probe_set)
    if rejected:
        write_json(Path(output_path).with_name(Path(output_path).stem + "_rejected.json"), rejected)
    return probe_set


def evaluate_retrieval(probe_set: list[dict[str, Any]], index, settings: Settings) -> dict[str, Any]:
    """Do rieng tang retrieval: hit@k, top1 va MRR. Khong goi LLM.

    MRR nhay hon hit@k: khi corruption day gold document tu rank 0 xuong rank 2, hit@k
    van la 1.0 nhung MRR giam -> thay duoc suy giam ma hit rate che mat.
    """
    top_k = settings.top_k
    details: list[dict[str, Any]] = []

    for item in probe_set:
        results = index.search(item["question"], top_k=top_k)
        retrieved = [result.paper_id for result in results]
        rank = next((i for i, doc_id in enumerate(retrieved) if doc_id in item["ground_truth_doc_ids"]), None)
        details.append(
            {
                "id": item["id"],
                "question": item["question"],
                "ground_truth_doc_ids": item["ground_truth_doc_ids"],
                "retrieved_doc_ids": retrieved,
                "rank": rank,
                "hit": rank is not None,
                "top1": rank == 0,
                "reciprocal_rank": 0.0 if rank is None else 1.0 / (rank + 1),
            }
        )

    total = len(details) or 1
    return {
        "samples": len(details),
        "top_k": top_k,
        f"retrieval_hit_rate_at_{top_k}": sum(1 for item in details if item["hit"]) / total,
        "top1_accuracy": sum(1 for item in details if item["top1"]) / total,
        "mrr": sum(item["reciprocal_rank"] for item in details) / total,
        "details": details,
    }
