from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests
from core.config import Settings, load_settings


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_abstract(raw_abstract: str) -> str:
    """Loại bỏ các thẻ HTML/JATS XML (như <jats:p>) khỏi abstract."""
    if not raw_abstract:
        return ""
    cleaned = re.sub(r"<[^>]+>", "", raw_abstract)
    return cleaned.strip()


def parse_crossref_payload(payload: dict[str, Any]) -> list[PaperRecord]:
    """Parse Crossref API payload thành danh sách PaperRecord."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        # Chuẩn hóa DOI thành lower-case làm stable paper_id
        raw_doi = item.get("DOI", "")
        if not raw_doi or not isinstance(raw_doi, str):
            continue
        paper_id = raw_doi.strip().lower()

        titles = item.get("title", [])
        title = titles[0].strip() if (titles and isinstance(titles[0], str)) else "Untitled"

        raw_abstract = item.get("abstract", "")
        summary = _clean_abstract(raw_abstract)

        authors: list[str] = []
        for author in item.get("author", []):
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            full_name = f"{given} {family}".strip() if (given or family) else author.get("name", "").strip()
            if full_name:
                authors.append(full_name)

        subjects = item.get("subject", [])
        categories = [s.strip() for s in subjects if isinstance(s, str) and s.strip()]
        primary_category = categories[0] if categories else "Uncategorized"

        published_date_parts = (
            item.get("published-print", {}).get("date-parts")
            or item.get("published-online", {}).get("date-parts")
            or item.get("created", {}).get("date-parts")
        )
        published = ""
        if published_date_parts and len(published_date_parts[0]) > 0:
            published = "-".join(f"{p:02d}" for p in published_date_parts[0])

        deposited_date_parts = item.get("deposited", {}).get("date-parts")
        updated = ""
        if deposited_date_parts and len(deposited_date_parts[0]) > 0:
            updated = "-".join(f"{p:02d}" for p in deposited_date_parts[0])

        abs_url = item.get("URL", f"https://doi.org/{paper_id}")
        pdf_url = ""
        for link in item.get("link", []):
            if link.get("content-type") == "application/pdf":
                pdf_url = link.get("URL", "")
                break

        publisher = item.get("publisher", "")
        # Safe-access chống IndexError khi container-title rỗng
        container_titles = item.get("container-title", [])
        container_title = container_titles[0] if container_titles else ""

        comment_parts = []
        if publisher:
            comment_parts.append(f"Publisher: {publisher}")
        if container_title:
            comment_parts.append(f"Journal: {container_title}")
        comment = "; ".join(comment_parts)

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Gọi Crossref API, lưu raw JSON response, parse và lưu raw records json."""
    url = "https://api.crossref.org/works"

    params = {
        "query": settings.source_query,
        "rows": settings.max_results,
    }
    if settings.source_filter:
        params["filter"] = settings.source_filter

    headers = {
        "User-Agent": "PaperFetcher/1.0 (mailto:your-email@example.com)"
    }

    max_retries = 3
    backoff_factor = 2
    payload = None

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            if response.status_code in (429, 503):
                if attempt == max_retries - 1:
                    response.raise_for_status()
                time.sleep(backoff_factor ** attempt)
                continue

            response.raise_for_status()
            payload = response.json()
            break
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"Lỗi khi gọi Crossref API sau {max_retries} lần thử: {e}") from e
            time.sleep(backoff_factor ** attempt)

    if payload is None:
        raise RuntimeError("Không thể nhận payload từ Crossref API.")

    # 1. Lưu RAW API Response vào đúng Contract Path
    raw_api_path = Path(settings.paths.raw_api_response)
    raw_api_path.parent.mkdir(parents=True, exist_ok=True)
    with open(raw_api_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # 2. Parse payload thành records
    records = parse_crossref_payload(payload)

    # 3. Lưu JSON Snapshot vào đúng Contract Path
    raw_records_path = Path(settings.paths.raw_records_json)
    raw_records_path.parent.mkdir(parents=True, exist_ok=True)
    with open(raw_records_path, "w", encoding="utf-8") as f:
        json.dump([asdict(rec) for rec in records], f, ensure_ascii=False, indent=2)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Đọc JSON snapshot và map ngược lại thành danh sách `PaperRecord`."""
    if not path.exists():
        raise FileNotFoundError(f"File không tồn tại: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return [PaperRecord(**item) for item in data]


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info("--- BẮT ĐẦU CHẠY INGESTION TEST ---")
    try:
        # Sử dụng load_settings chuẩn từ core.config
        settings = load_settings()
        records = fetch_source_records(settings)
        logger.info(f"SUCCESS: Fetch và parse thành công {len(records)} bài báo!")
    except Exception as err:
        logger.error(f"FAILED: Có lỗi xảy ra: {err}", exc_info=True)