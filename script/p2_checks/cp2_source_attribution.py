"""CP2 — Cung cấp bằng chứng nguồn cho một ``paper_id``.

Nhiệm vụ CP2 của Vai trò 2: khi evaluator hoặc agent trả lời sai, người đo cần
biết dữ liệu gốc thực sự nói gì trước khi kết luận "RAG kém". Module này trả về
bằng chứng từ **cả hai** tầng raw và clean, vì lỗi có thể nằm ở khâu parse
(raw sai) hoặc khâu cleaning (raw đúng nhưng clean sai).

Dùng như module:
    from cp2_source_attribution import SourceAttribution
    SourceAttribution().get_evidence("10.2118/234689-pa")

Hoặc chạy trực tiếp:
    python script/p2_checks/cp2_source_attribution.py [paper_id]
"""

from __future__ import annotations

import json
import sys
from typing import Any

from _common import header, settings, setup_console

DEFAULT_PAPER_ID = "10.2118/234689-pa"


class SourceAttribution:
    """Tra cứu bằng chứng nguồn theo ``paper_id``."""

    def __init__(self) -> None:
        cfg = settings()
        self._raw = {
            item["paper_id"]: item
            for item in json.loads(cfg.paths.raw_records_json.read_text(encoding="utf-8"))
        }
        self._clean = {
            item["paper_id"]: item
            for item in json.loads(cfg.paths.clean_json.read_text(encoding="utf-8"))
        }

    def get_evidence(self, paper_id: str) -> dict[str, Any]:
        raw = self._raw.get(paper_id)
        clean = self._clean.get(paper_id)

        if raw is None and clean is None:
            return {
                "paper_id": paper_id,
                "error": "Không tìm thấy ở cả tầng raw lẫn tầng clean.",
                "hint": "paper_id sai, hoặc bản ghi đã bị corruption xoá — đối chiếu corruption_log.json.",
            }

        evidence: dict[str, Any] = {
            "paper_id": paper_id,
            "found_in_raw": raw is not None,
            "found_in_clean": clean is not None,
        }

        # Có ở raw nhưng mất ở clean là tín hiệu quan trọng: cleaning đã loại bản
        # ghi này. Ghi rõ ra thay vì trả về dict rỗng, vì đây chính là đầu mối
        # cần cho người đo.
        if raw is not None and clean is None:
            evidence["warning"] = "Có ở raw nhưng đã bị cleaning loại bỏ — xem data/quality/cleaning_report.json."

        source = clean or raw
        evidence.update(
            {
                "title": source.get("title"),
                "published": source.get("published"),
                "authors": source.get("authors_joined") or ", ".join(source.get("authors", [])),
                "categories": source.get("categories_joined") or ", ".join(source.get("categories", [])),
                "summary_excerpt": (source.get("summary") or "")[:300],
                "abs_url": source.get("abs_url"),
                "comment": source.get("comment"),
            }
        )

        # Đối chiếu raw ↔ clean trên các trường mà agent dùng để trả lời. Lệch ở
        # đây nghĩa là câu trả lời sai bắt nguồn từ cleaning, không phải retrieval.
        if raw is not None and clean is not None:
            drift = {
                field: {"raw": raw.get(field), "clean": clean.get(field)}
                for field in ("title", "published")
                if str(raw.get(field, "")).strip() != str(clean.get(field, "")).strip()
            }
            evidence["raw_vs_clean_drift"] = drift or "không lệch"

        return evidence


if __name__ == "__main__":
    setup_console()
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PAPER_ID
    header(f"CP2 — BẰNG CHỨNG NGUỒN: {target}")
    print(json.dumps(SourceAttribution().get_evidence(target), ensure_ascii=False, indent=2))
