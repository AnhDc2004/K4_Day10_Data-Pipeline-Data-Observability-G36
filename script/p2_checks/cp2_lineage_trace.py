"""CP2 — Truy vết một ``paper_id`` xuyên suốt raw response → raw records → clean → index.

Đây là nhiệm vụ CP2 của Vai trò 2: chứng minh một bản ghi đi hết 4 tầng mà
không đứt mạch, để khi evaluator hoặc agent trả lời sai thì có bằng chứng nguồn
để đối chiếu.

Chạy:
    python script/p2_checks/cp2_lineage_trace.py [paper_id]

Mặc định truy vết ``10.2118/234689-pa`` — chính là một trong hai bản ghi bị
kịch bản ``drop_latest`` xoá ở CP5, nên nó cũng là mẫu dùng lại ở CP6.
"""

from __future__ import annotations

import json
import sys

import pandas as pd

from _common import header, raw_response_dois, section, settings, setup_console, summarize, verdict

DEFAULT_PAPER_ID = "10.2118/234689-pa"


def trace(paper_id: str) -> int:
    cfg = settings()
    results: list[bool] = []

    header(f"CP2 — LINEAGE TRACE: {paper_id}")

    # --- Tầng 1: raw API response (nguyên trạng, trước khi parse) ---
    section("Tầng 1/4 · raw API response")
    payload = json.loads(cfg.paths.raw_api_response.read_text(encoding="utf-8"))
    dois = raw_response_dois(payload)
    results.append(
        verdict(
            paper_id in dois,
            f"DOI có trong '{cfg.paths.raw_api_response.name}' ({len(dois)} DOI trong response)",
        )
    )

    # --- Tầng 2: raw records đã parse thành PaperRecord ---
    section("Tầng 2/4 · raw records đã parse")
    records = json.loads(cfg.paths.raw_records_json.read_text(encoding="utf-8"))
    record = next((r for r in records if r.get("paper_id") == paper_id), None)
    results.append(
        verdict(record is not None, f"paper_id có trong '{cfg.paths.raw_records_json.name}' ({len(records)} record)")
    )
    if record:
        print(f"        title    : {record['title'][:70]}")
        print(f"        published: {record['published']}")
        print(f"        authors  : {len(record['authors'])} tác giả")

    # --- Tầng 3: clean dataframe ---
    section("Tầng 3/4 · clean dataset")
    df = pd.read_csv(cfg.paths.clean_csv, dtype={"paper_id": str})
    row = df[df["paper_id"] == paper_id]
    results.append(verdict(not row.empty, f"paper_id có trong '{cfg.paths.clean_csv.name}' ({len(df)} dòng)"))
    if not row.empty:
        item = row.iloc[0]
        print(f"        age_days      : {item['age_days']}")
        print(f"        summary_chars : {item['summary_chars']}")
        # So title raw ↔ clean: cleaning được phép chuẩn hoá khoảng trắng nhưng
        # không được đổi nội dung. Lệch ở đây nghĩa là đứt mạch lineage.
        if record:
            same_title = str(item["title"]).strip() == record["title"].strip()
            results.append(verdict(same_title, "title ở tầng clean khớp với tầng raw (không bị đổi nội dung)"))

    # --- Tầng 4: vector index ---
    section("Tầng 4/4 · ChromaDB index")
    results.append(_check_index(cfg, paper_id))

    return summarize(results)


def _check_index(cfg, paper_id: str) -> bool:
    """Tra ``paper_id`` trong collection baseline.

    Index không được commit đầy đủ (``chroma.sqlite3`` nằm trong ``.gitignore``)
    nên trên bản clone sạch collection sẽ không tồn tại. Trường hợp đó phải báo
    "chưa kiểm chứng được" chứ không được in OK — một kiểm tra luôn xanh thì vô
    nghĩa.
    """
    try:
        import chromadb

        client = chromadb.PersistentClient(path=str(cfg.paths.chroma_dir))
        names = [c.name if hasattr(c, "name") else str(c) for c in client.list_collections()]
        if cfg.baseline_collection_name not in names:
            print(
                f"   [SKIP] Chưa có collection '{cfg.baseline_collection_name}' trong "
                f"'{cfg.paths.chroma_dir}' (collection hiện có: {names or 'không có'})."
            )
            print("          Nguyên nhân: 'data/chroma/chroma.sqlite3' bị .gitignore nên bản")
            print("          clone không có metadata collection. Chạy 'python script/run_phase1.py'")
            print("          để build lại index rồi chạy lại script này.")
            return False

        collection = client.get_collection(cfg.baseline_collection_name)
        found = collection.get(ids=[paper_id])
        ok = bool(found and found.get("ids"))
        verdict(ok, f"paper_id có trong collection '{cfg.baseline_collection_name}' ({collection.count()} doc)")
        if ok and found.get("metadatas"):
            print(f"        metadata: {found['metadatas'][0]}")
        return ok
    except Exception as err:  # noqa: BLE001 — báo nguyên văn lỗi thay vì nuốt
        print(f"   [SKIP] Không mở được ChromaDB: {err}")
        return False


if __name__ == "__main__":
    setup_console()
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PAPER_ID
    raise SystemExit(trace(target))
