"""Tiện ích dùng chung cho bộ kiểm tra của Vai trò 2 (Ingestion owner).

Mọi đường dẫn đều lấy từ ``core.load_settings()`` thay vì hard-code chuỗi
``"data/raw"``, để bộ kiểm tra chạy đúng kể cả khi project được đặt ở thư mục
khác — đây là lỗi hard-code path mà Rubric trừ điểm.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

from core import load_settings
from core.config import Settings


def setup_console() -> None:
    """Ép stdout sang UTF-8.

    Console Windows mặc định là cp1252 nên mọi ký tự tiếng Việt có dấu sẽ ném
    ``UnicodeEncodeError`` giữa chừng và làm script chết trước khi in kết luận.
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass


def settings() -> Settings:
    return load_settings()


def header(title: str) -> None:
    print("=" * 68)
    print(f" {title}")
    print("=" * 68)


def section(title: str) -> None:
    print(f"\n--- {title} ---")


def verdict(ok: bool, message: str) -> bool:
    """In một dòng kết luận và trả lại chính ``ok`` để caller cộng dồn."""
    print(f"   [{'OK' if ok else 'FAIL'}] {message}")
    return ok


def summarize(results: list[bool]) -> int:
    """In tổng kết và trả về exit code (0 = mọi kiểm tra đạt)."""
    passed = sum(1 for r in results if r)
    total = len(results)
    print("\n" + "-" * 68)
    if passed == total:
        print(f" KẾT LUẬN: {passed}/{total} kiểm tra ĐẠT.")
        return 0
    print(f" KẾT LUẬN: {passed}/{total} kiểm tra đạt — {total - passed} mục KHÔNG ĐẠT.")
    return 1


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def raw_response_dois(payload: dict[str, Any]) -> set[str]:
    """Rút tập DOI từ raw API response.

    Chuẩn hoá về chữ thường đúng như ``parse_crossref_payload`` để so khớp được
    với ``paper_id`` ở các tầng sau; nếu không, mọi so sánh raw ↔ clean đều lệch
    khi Crossref trả DOI viết hoa.
    """
    items = payload.get("message", {}).get("items", [])
    return {str(item.get("DOI", "")).strip().lower() for item in items if item.get("DOI")}
