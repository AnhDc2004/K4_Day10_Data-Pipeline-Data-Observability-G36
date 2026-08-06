import json
import pandas as pd
import chromadb
from pathlib import Path

# Chọn paper_id mà bạn vừa lấy từ dữ liệu clean của nhóm
TARGET_PAPER_ID = "10.2118/234689-pa"

def audit_paper_lineage(paper_id: str):
    print(f"=== Đang kiểm tra lineage cho paper_id: {paper_id} ===")
    
    # --- 1. KIỂM TRA TẦNG RAW ---
    raw_dir = Path("data/raw")
    raw_found = False
    if raw_dir.exists():
        for file_path in raw_dir.glob("*.json"):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    content = json.load(f)
                    items = content if isinstance(content, list) else content.get("items", [])
                    if any(item.get("DOI") == paper_id or item.get("paper_id") == paper_id for item in items):
                        raw_found = True
                        break
                except Exception:
                    pass
    if raw_found:
        print(" [tầng RAW] [OK] Tìm thấy trong dữ liệu thô gốc.")
    else:
        print(" [tầng RAW] [!] Không tìm thấy (hoặc thư mục raw trống/khác cấu trúc, có thể bỏ qua nếu bạn dùng dữ liệu clean làm gốc).")

    # --- 2. KIỂM TRA TẦNG CLEAN ---
    clean_dir = Path("data/clean")
    clean_found = False
    clean_title = ""
    if clean_dir.exists():
        for file_path in clean_dir.glob("*.json"):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    # Đảm bảo data là list (danh sách các bài báo)
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get("paper_id") == paper_id:
                                clean_found = True
                                clean_title = item.get("title", "")
                                break
                    elif isinstance(data, dict):
                        # Trường hợp file json bọc dưới dạng dict
                        items = data.get("items", [])
                        for item in items:
                            if isinstance(item, dict) and item.get("paper_id") == paper_id:
                                clean_found = True
                                clean_title = item.get("title", "")
                                break
                except Exception:
                    pass
            if clean_found:
                break
            
    if clean_found:
        print(f" [tầng CLEAN] [OK] Tìm thấy trong file clean.")
        print(f"    -> Tiêu đề: {clean_title}")
    else:
        print(" [tầng CLEAN] [X] Không tìm thấy paper_id này trong thư mục clean!")
        return

    # --- 3. KIỂM TRA TẦNG INDEX (ChromaDB) ---
    try:
        # Đường dẫn tới thư mục lưu ChromaDB của nhóm bạn (thường là data/embeddings hoặc tương tự)
        client = chromadb.PersistentClient(path="data/embeddings") 
        collection = client.get_collection("papers-baseline")
        
        results = collection.get(ids=[paper_id])
        if results and results['ids'] and len(results['ids']) > 0:
            print(f" [tầng INDEX] [OK] Tìm thấy trong ChromaDB collection 'papers-baseline'!")
            print(f"    -> Metadata đã index: {results['metadatas'][0] if results['metadatas'] else 'Không có metadata'}")
        else:
            print(" [tầng INDEX] [X] CẢNH BÁO: Tìm thấy ở Clean nhưng CHƯA ĐƯỢC INDEX vào ChromaDB!")
    except Exception as e:
        print(f" [tầng INDEX] [!] Lỗi kết nối ChromaDB: {e}")

if __name__ == "__main__":
    audit_paper_lineage(TARGET_PAPER_ID)
