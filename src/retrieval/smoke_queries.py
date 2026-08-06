"""Stable manual queries for the RAG handoff and CP2 smoke test."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SmokeQuery:
    """A query that can be checked against a clean paper corpus."""

    name: str
    question: str
    lookup_value: str | None = None


SMOKE_QUERIES = (
    SmokeQuery(
        name="semantic_topic",
        question="Which papers discuss agentic retrieval augmented generation?",
    ),
    SmokeQuery(
        name="exact_paper_id",
        question="Look up the paper by its exact paper ID.",
        lookup_value="<paper_id from clean data>",
    ),
    SmokeQuery(
        name="exact_title",
        question="Look up the paper by its exact title.",
        lookup_value="<title from clean data>",
    ),
    SmokeQuery(
        name="authors",
        question="Who authored the selected paper?",
    ),
    SmokeQuery(
        name="publication_date",
        question="When was the selected paper published?",
    ),
    SmokeQuery(
        name="categories",
        question="What categories does the selected paper belong to?",
    ),
)

