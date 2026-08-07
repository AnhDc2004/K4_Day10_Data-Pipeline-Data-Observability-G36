"""CP3 — Xác minh raw artifact còn đọc được và ghi lại vân tay toàn vẹn.

Nhiệm vụ CP3 của Vai trò 2: trước khi baseline được chốt, phải chứng minh
``crossref_response.json`` và ``crossref_records.json`` vẫn đọc được, khớp nhau,
và ghi lại sha256 của chúng làm mốc so sánh cho CP5/CP6.

Bản gốc ở CP3 chỉ đếm ``len()`` của mọi file ``*.json`` trong ``data/raw`` rồi
cộng dồn — cách đó cho ra số đúng chỉ do may (raw response là dict nên
``.get("items")`` trả về rỗng). Bản này đọc đúng cấu trúc từng file.

Chạy:
    python script/p2_checks/cp3_verify_raw.py
"""

from __future__ import annotations

import json

from _common import header, raw_response_dois, section, settings, setup_console, sha256_of, summarize, verdict

INTEGRITY_FILENAME = "p2_raw_integrity.json"


def verify_raw() -> int:
    cfg = settings()
    results: list[bool] = []

    header("CP3 — XÁC MINH RAW ARTIFACT & GHI VÂN TAY TOÀN VẸN")

    # --- 1. Hai artifact raw có tồn tại và parse được không ---
    section("1/4 · Đọc raw artifact")
    for path in (cfg.paths.raw_api_response, cfg.paths.raw_records_json):
        try:
            json.loads(path.read_text(encoding="utf-8"))
            results.append(verdict(True, f"'{path.name}' đọc và parse JSON thành công ({path.stat().st_size:,} bytes)"))
        except Exception as err:  # noqa: BLE001
            results.append(verdict(False, f"'{path.name}' KHÔNG đọc được: {err}"))
            return summarize(results)

    payload = json.loads(cfg.paths.raw_api_response.read_text(encoding="utf-8"))
    records = json.loads(cfg.paths.raw_records_json.read_text(encoding="utf-8"))

    # --- 2. Số bản ghi ở response và ở records có khớp không ---
    section("2/4 · Đối chiếu response ↔ records")
    items = payload.get("message", {}).get("items", [])
    print(f"   items trong raw response : {len(items)}")
    print(f"   record đã parse          : {len(records)}")
    results.append(
        verdict(
            len(items) == len(records),
            "parse không làm rơi bản ghi nào (mọi item đều thành PaperRecord)",
        )
    )

    dois = raw_response_dois(payload)
    parsed_ids = {r["paper_id"] for r in records}
    missing = sorted(dois - parsed_ids)
    results.append(verdict(not missing, f"mọi DOI trong response đều có paper_id tương ứng (thiếu: {len(missing)})"))
    if missing:
        for doi in missing[:5]:
            print(f"        thiếu: {doi}")

    # --- 3. paper_id có ổn định và duy nhất không ---
    section("3/4 · Chất lượng định danh")
    results.append(verdict(len(parsed_ids) == len(records), f"paper_id duy nhất ({len(parsed_ids)}/{len(records)})"))
    results.append(
        verdict(
            all(r["paper_id"] == r["paper_id"].strip().lower() for r in records),
            "paper_id đã chuẩn hoá chữ thường — so khớp giữa các tầng không lệch vì hoa/thường",
        )
    )

    # --- 4. Ghi vân tay để CP5/CP6 đối chiếu ---
    section("4/4 · Vân tay toàn vẹn")
    fingerprint = {
        "raw_api_response": {
            "file": cfg.paths.raw_api_response.name,
            "sha256": sha256_of(cfg.paths.raw_api_response),
            "items": len(items),
        },
        "raw_records": {
            "file": cfg.paths.raw_records_json.name,
            "sha256": sha256_of(cfg.paths.raw_records_json),
            "records": len(records),
        },
    }
    output = cfg.paths.quality_dir / INTEGRITY_FILENAME
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(fingerprint, indent=2) + "\n", encoding="utf-8")
    for key, value in fingerprint.items():
        print(f"   {key}: {value['sha256'][:16]}…")
    results.append(verdict(True, f"đã ghi vân tay ra '{output}'"))

    # Ghi rõ một giới hạn đã biết thay vì để người đọc tự suy ra
    section("Ghi chú giới hạn")
    empty_categories = sum(1 for r in records if not r.get("categories"))
    if empty_categories:
        print(
            f"   [!] {empty_categories}/{len(records)} record có 'categories' rỗng — Crossref không trả\n"
            f"       field 'subject' cho query này. Xem mục 6 trong báo cáo cá nhân Vai trò 2."
        )

    return summarize(results)


if __name__ == "__main__":
    setup_console()
    raise SystemExit(verify_raw())
