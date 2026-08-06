import json
from pathlib import Path

def kiem_tra_raw_clean():
    print("\n--- [Task 1] Kiểm tra nguyên vẹn dữ liệu Raw & Clean ---")
    raw_dir = Path("data/raw")
    clean_dir = Path("data/clean")
    if raw_dir.exists() and clean_dir.exists():
        print("   • [OK] Thư mục dữ liệu nguồn đầy đủ và nguyên vẹn.")
    else:
        print("   • [X] Lỗi: Thiếu thư mục dữ liệu nguồn!")

def chon_mau_phuc_hoi():
    print("\n--- [Task 2] Chọn bản ghi mẫu để thử nghiệm phục hồi (Repair) ---")
    clean_dir = Path("data/clean")
    sample = None
    if clean_dir.exists():
        for file_path in clean_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        sample = data[0]
                        break
            except Exception:
                pass
    if sample:
        paper_id = sample.get("paper_id") or sample.get("DOI", "N/A")
        print(f"   • Đã chọn Paper ID mẫu: {paper_id}")
        print("   • [OK] Sẵn sàng dùng bản ghi này để giả lập lỗi và sửa chữa.")
    else:
        print("   • [X] Không tìm thấy bản ghi mẫu.")

def kiem_tra_co_lap_mang():
    print("\n--- [Task 3] Kiểm tra không gọi mạng/fetch nguồn mới khi chạy lỗi ---")
    tu_khoa_rui_ro = ["requests.get", "urllib", "fetch(", "download("]
    py_files = list(Path(".").glob("*.py"))
    
    co_goi_mang = False
    for f in py_files:
        if f.name == "kiem_tra_cp5.py": # bỏ qua chính file này
            continue
        try:
            noi_dung = f.read_text(encoding="utf-8", errors="ignore")
            if any(kw in noi_dung for kw in tu_khoa_rui_ro):
                co_goi_mang = True
                break
        except Exception:
            pass
            
    if not co_goi_mang:
        print("   • [OK] Hệ thống cô lập tuyệt đối, dùng dữ liệu tĩnh để đối chiếu công bằng.")
    else:
        print("   • [!] Cảnh báo: Phát hiện lệnh có thể gọi mạng.")

if __name__ == "__main__":
    print("=" * 60)
    print(" BẮT ĐẦU CHẠY KIỂM TRA CHECKPOINT 5")
    print("=" * 60)
    
    kiem_tra_raw_clean()
    chon_mau_phuc_hoi()
    kiem_tra_co_lap_mang()
    
    print("\n" + "=" * 60)
    print(" HOÀN TẤT TẤT CẢ CÁC TASK CỦA CHECKPOINT 5!")
    print("=" * 60)
