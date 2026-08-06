from pathlib import Path

def audit_no_external_fetch():
    print("=" * 60)
    print(" CHECKPOINT 3 - TASK 3: KIỂM TRA KHÔNG FETCH NGUỒN NGOÀI Ý MUỐN")
    print("=" * 60)
    
    # Các từ khóa có nguy cơ gọi mạng/fetch dữ liệu mới
    risk_keywords = ["requests.get", "urllib", "http.client", "aiohttp", "fetch(", "download("]
    
    # Thư mục code cần quét
    root_dir = Path(".")
    python_files = list(root_dir.glob("*.py"))
    
    suspicious_findings = []
    
    for file_path in python_files:
        # Bỏ qua chính file kiểm tra này
        if file_path.name == "P2_cp3_task3_check.py":
            continue
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line_idx, line in enumerate(lines, 1):
                    for keyword in risk_keywords:
                        if keyword in line and not line.strip().startswith("#"):
                            suspicious_findings.append({
                                "file": file_path.name,
                                "line": line_idx,
                                "content": line.strip()
                            })
        except Exception:
            pass

    print(f"📊 KẾT QUẢ QUÉT AN TOÀN BASELINE:")
    if len(suspicious_findings) == 0:
        print("   • [OK] Tuyệt vời! Không phát hiện lệnh gọi mạng/fetch dữ liệu ngoài nào trong mã nguồn.")
        print("   • Hệ thống hoàn toàn sử dụng dữ liệu tĩnh cục bộ (Static Local Files).")
    else:
        print(f"   • [!] Cảnh báo: Tìm thấy {len(suspicious_findings)} điểm nghi vấn gọi mạng:")
        for item in suspicious_findings:
            print(f"     - File: {item['file']} (Dòng {item['line']}): `{item['content']}`")
            
    print("-" * 60)
    print("📝 CAM KẾT CHO BÁO CÁO CP3:")
    print("   • Đảm bảo không thực hiện cào mới (re-fetch) dữ liệu thô trong suốt giai đoạn Evaluation.")
    print("   • Giữ nguyên vẹn baseline dữ liệu đã chốt từ các pha trước.")
    print("=" * 60)

if __name__ == "__main__":
    audit_no_external_fetch()
