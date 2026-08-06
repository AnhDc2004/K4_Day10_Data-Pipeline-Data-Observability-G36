import json
from pathlib import Path

def compare_raw_clean_counts():
    print("=" * 60)
    print(" CHECKPOINT 3 - TASK 2: SO SÁNH RAW & CLEAN COUNT")
    print("=" * 60)
    
    # 1. Đếm tổng số bản ghi ở tầng RAW
    raw_dir = Path("data/raw")
    raw_count = 0
    if raw_dir.exists():
        for file_path in raw_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    items = content if isinstance(content, list) else content.get("items", [])
                    raw_count += len(items)
            except Exception:
                pass

    # 2. Đếm tổng số bản ghi ở tầng CLEAN
    clean_dir = Path("data/clean")
    clean_count = 0
    if clean_dir.exists():
        for file_path in clean_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        clean_count += len(data)
            except Exception:
                pass

    # 3. Tính toán chênh lệch
    diff = raw_count - clean_count
    diff_percent = (diff / raw_count * 100) if raw_count > 0 else 0

    print(f"📊 KẾT QUẢ THỐNG KÊ:")
    print(f"   • Tổng số bản ghi tầng RAW   : {raw_count}")
    print(f"   • Tổng số bản ghi tầng CLEAN : {clean_count}")
    print(f"   • Số lượng chênh lệch (Drop): {diff} bản ghi ({diff_percent:.2f}%)")
    
    print("-" * 60)
    print("📝 GIẢI THÍCH LÝ DO CHÊNH LỆCH (DÙNG CHO BÁO CÁO CP3):")
    print("   1. Lọc bỏ trùng lặp (Deduplication): Loại bỏ các bản ghi bị lặp DOI/Paper ID.")
    print("   2. Kiểm tra tính hợp lệ (Data Cleaning): Loại bỏ các bản ghi thiếu các trường dữ liệu bắt buộc (ví dụ: thiếu tiêu đề, thiếu định danh DOI hợp lệ).")
    print("   3. Chuẩn hóa định dạng (Normalization): Đồng bộ hóa cấu trúc dữ liệu trước khi đưa vào Index.")
    print("=" * 60)

if __name__ == "__main__":
    compare_raw_clean_counts()
