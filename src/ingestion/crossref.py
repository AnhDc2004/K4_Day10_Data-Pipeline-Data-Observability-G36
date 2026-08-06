from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests
from core.config import Settings


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
    # Strip XML/HTML tags
    cleaned = re.sub(r"<[^>]+>", "", raw_abstract)
    return cleaned.strip()


def parse_crossref_payload(payload: dict[str, Any]) -> list[PaperRecord]:
    """Parse Crossref API payload thành danh sách PaperRecord."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        doi = item.get("DOI", "").strip()
        if not doi:
            continue

        titles = item.get("title", [])
        title = titles[0].strip() if titles else "Untitled"

        raw_abstract = item.get("abstract", "")
        summary = _clean_abstract(raw_abstract)

        authors = []
        for author in item.get("author", []):
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            full_name = f"{given} {family}".strip() if (given or family) else author.get("name", "").strip()
            if full_name:
                authors.append(full_name)

        subjects = item.get("subject", [])
        categories = [s.strip() for s in subjects if isinstance(s, str)]
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

        abs_url = item.get("URL", f"https://doi.org/{doi}")
        pdf_url = ""
        for link in item.get("link", []):
            if link.get("content-type") == "application/pdf":
                pdf_url = link.get("URL", "")
                break

        publisher = item.get("publisher", "")
        container_title = item.get("container-title", [""])[0]
        comment = f"Publisher: {publisher}; Journal: {container_title}".strip(" ;")

        record = PaperRecord(
            paper_id=doi,
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
        records.append(record)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Gọi Crossref API, lưu raw JSON response, parse và lưu raw records json."""
    url = "https://api.crossref.org/works"
    
    params = {
        "query": getattr(settings, "source_query", "machine learning"),
        "rows": getattr(settings, "max_results", 20),
    }
    
    if hasattr(settings, "source_filter") and settings.source_filter:
        params["filter"] = settings.source_filter

    headers = {
        "User-Agent": "PaperFetcher/1.0 (mailto:your-email@example.com)"
    }

    max_retries = 3
    backoff_factor = 2

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            if response.status_code in (429, 503):
                time.sleep(backoff_factor ** attempt)
                continue
            response.raise_for_status()
            payload = response.json()
            break
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"Lỗi khi gọi Crossref API sau {max_retries} lần thử: {e}")
            time.sleep(backoff_factor ** attempt)

    raw_api_path = Path(settings.paths.raw_api_response)
    raw_api_path.parent.mkdir(parents=True, exist_ok=True)
    with open(raw_api_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    records = parse_crossref_payload(payload)

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
    
    # 1. Khởi tạo Settings (hoặc mock nếu chưa setup pydantic)
    try:
        settings = Settings()
    except Exception as e:
        logger.warning(f"Không thể load Settings từ config ({e}), khởi tạo mock settings...")
        
        # Mock class tạm thời nếu bạn chưa config Settings
        class MockPaths:
            raw_api_response = "data/raw/crossref_raw_response.json"
            raw_records_json = "data/raw/crossref_records.json"

        class MockSettings:
            source_query = "machine learning"
            source_filter = ""
            max_results = 5
            paths = MockPaths()
            
        settings = MockSettings()

    # 2. Gọi hàm Fetch & Lưu dữ liệu
    try:
        logger.info(f"Đang fetch dữ liệu từ Crossref API (query: '{getattr(settings, 'source_query', 'N/A')}') ...")
        records = fetch_source_records(settings)
        
        logger.info(" SUCCESS: Fetch và parse thành công!")
        logger.info(f"Tổng số bài báo thu thập được: {len(records)}")
        
        if records:
            sample = records[0]
            logger.info("--- MẪU BÀI BÁO ĐẦU TIÊN ---")
            logger.info(f"Paper ID (DOI): {sample.paper_id}")
            logger.info(f"Title: {sample.title}")
            logger.info(f"Authors: {sample.authors}")
            logger.info(f"Published: {sample.published}")
            logger.info(f"PDF URL: {sample.pdf_url}")
            
        logger.info("--- ĐÃ LƯU FILE RAW VÀ RECORDS VÀO THƯ MỤC DATA/RAW/ ---")

    except Exception as e:
        logger.error(f" FAILED: Có lỗi xảy ra trong quá trình chạy ingestion: {e}", exc_info=True)