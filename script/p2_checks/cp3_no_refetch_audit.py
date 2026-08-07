"""CP3 — Kiểm tra pipeline không fetch lại nguồn ngoài ý muốn.

Nhiệm vụ CP3/CP5 của Vai trò 2: baseline chỉ so sánh được với corrupted và
repaired nếu cả ba chạy trên **cùng một snapshot**. Một lần fetch lại giữa chừng
là đổi đề bài, và mọi chênh lệch metric sau đó mất ý nghĩa.

Bản gốc quét ``Path(".").glob("*.py")`` — chỉ các file ``.py`` ở thư mục gốc.
Toàn bộ code thật nằm trong ``src/`` nên phép quét không nhìn thấy gì và luôn in
"không phát hiện gọi mạng": một kiểm tra không bao giờ đỏ. Bản này quét đúng
``src/``, và vì ``crossref.py`` **buộc phải** có ``requests.get``, trọng tâm
chuyển từ "có gọi mạng không" sang "lệnh gọi mạng có bị chặn bởi guard không".

Chạy:
    python script/p2_checks/cp3_no_refetch_audit.py
"""

from __future__ import annotations

import json
import os
import re

from _common import header, section, settings, setup_console, sha256_of, summarize, verdict
from cp3_verify_raw import INTEGRITY_FILENAME

NETWORK_PATTERNS = ("requests.get", "requests.post", "urllib.request", "http.client", "aiohttp", "httpx")

# Nơi duy nhất được phép gọi mạng theo phân công vai trò.
ALLOWED_NETWORK_FILE = "crossref.py"


def audit() -> int:
    cfg = settings()
    results: list[bool] = []

    header("CP3 — AUDIT: PIPELINE KHÔNG FETCH LẠI NGUỒN")

    # --- 1. Lệnh gọi mạng nằm ở đâu trong src/ ---
    section("1/4 · Vị trí lệnh gọi mạng trong src/")
    src_dir = cfg.paths.project_dir / "src"
    findings: list[tuple[str, int, str]] = []
    for path in sorted(src_dir.rglob("*.py")):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if any(pattern in stripped for pattern in NETWORK_PATTERNS):
                findings.append((path.name, line_no, stripped))

    for name, line_no, text in findings:
        print(f"   {name}:{line_no}  {text[:60]}")
    unexpected = [f for f in findings if f[0] != ALLOWED_NETWORK_FILE]
    results.append(
        verdict(
            not unexpected,
            f"lệnh gọi mạng chỉ nằm trong '{ALLOWED_NETWORK_FILE}' ({len(findings)} vị trí, ngoài luồng: {len(unexpected)})",
        )
    )

    # --- 2. Lệnh fetch có bị guard không ---
    section("2/4 · Guard quanh fetch_source_records")
    phase1 = (src_dir / "pipelines" / "phase1.py").read_text(encoding="utf-8")
    guarded = re.search(r"if\s+.*exists\(\).*refresh_source", phase1) is not None
    results.append(verdict(guarded, "phase1.py chỉ fetch khi thiếu snapshot HOẶC refresh_source=True"))

    corruption_flow = (src_dir / "pipelines" / "corruption_flow.py").read_text(encoding="utf-8")
    results.append(
        verdict(
            "fetch_source_records" not in corruption_flow,
            "corruption_flow.py không gọi fetch_source_records — corrupted/repaired dùng lại đúng snapshot",
        )
    )
    results.append(
        verdict(
            "load_raw_records" in corruption_flow,
            "corruption_flow.py repair bằng load_raw_records (đọc snapshot), không cào lại nguồn",
        )
    )

    # --- 3. Biến môi trường có đang bật refresh không ---
    section("3/4 · Biến môi trường")
    refresh = os.getenv("REFRESH_SOURCE", "")
    results.append(
        verdict(
            refresh.lower() not in {"1", "true", "yes"},
            f"REFRESH_SOURCE không bật (giá trị hiện tại: {refresh or 'không đặt'})",
        )
    )

    # --- 4. Snapshot có thay đổi so với vân tay đã ghi ở CP3 không ---
    section("4/4 · Vân tay snapshot")
    results.append(_compare_fingerprint(cfg))

    return summarize(results)


def _compare_fingerprint(cfg) -> bool:
    """So sha256 hiện tại với vân tay ghi ở ``cp3_verify_raw.py``.

    Đây là bằng chứng duy nhất chứng minh snapshot **thực sự** không đổi giữa các
    lần chạy; ba mục trên chỉ chứng minh code không có đường dẫn tới việc fetch.
    """
    recorded_path = cfg.paths.quality_dir / INTEGRITY_FILENAME
    if not recorded_path.exists():
        print(f"   [SKIP] Chưa có '{recorded_path.name}'. Chạy cp3_verify_raw.py trước để ghi mốc.")
        return False

    recorded = json.loads(recorded_path.read_text(encoding="utf-8"))
    pairs = (
        ("raw_api_response", cfg.paths.raw_api_response),
        ("raw_records", cfg.paths.raw_records_json),
    )
    unchanged = True
    for key, path in pairs:
        current = sha256_of(path)
        expected = recorded.get(key, {}).get("sha256")
        if current == expected:
            print(f"   {path.name}: khớp vân tay ({current[:16]}…)")
        else:
            unchanged = False
            print(f"   {path.name}: ĐÃ ĐỔI — ghi nhận {str(expected)[:16]}… nhưng hiện tại {current[:16]}…")
    return verdict(unchanged, "snapshot raw không đổi kể từ lúc ghi vân tay")


if __name__ == "__main__":
    setup_console()
    raise SystemExit(audit())
