# Bộ kiểm tra của Vai trò 2 — Ingestion & raw lineage

Các script trong thư mục này phục vụ nhiệm vụ CP2, CP3, CP5, CP6 của Vai trò 2
(Nguyễn Thành Huy — 2A202601802). Chúng **không** nằm trong đường chạy của
`run_phase1.py` hay `run_corruption_flow.py`: đây là kiểm tra độc lập chạy sau
pipeline để xác minh bằng chứng, nên chạy hay không chạy đều không đổi artifact
của nhóm.

## Chạy

Cần `.venv` đã kích hoạt và project đã cài (`python -m pip install -e .`).

```bash
python script/p2_checks/cp2_lineage_trace.py           # có thể truyền paper_id
python script/p2_checks/cp2_source_attribution.py      # có thể truyền paper_id
python script/p2_checks/cp3_verify_raw.py              # chạy trước 2 script dưới
python script/p2_checks/cp3_compare_counts.py
python script/p2_checks/cp3_no_refetch_audit.py
python script/p2_checks/cp5_pre_corruption_check.py    # sau run_corruption_flow.py
python script/p2_checks/cp6_repair_lineage_proof.py    # sau run_corruption_flow.py
```

Mỗi script trả exit code `0` khi mọi kiểm tra đạt, `1` khi có mục không đạt —
dùng được trong CI.

`cp3_verify_raw.py` ghi ra `data/quality/p2_raw_integrity.json` (sha256 của hai
file raw). Hai script CP3/CP5 sau đó đối chiếu với vân tay này để chứng minh
snapshot không đổi giữa các lần chạy. Đây là artifact duy nhất bộ kiểm tra này
tạo ra.

## Nguồn gốc và những gì đã sửa

Bản gốc do tôi viết trong các commit `58bc843` (CP2), `281c19b` (CP3),
`8098a50` (CP5), sau đó bị xoá khỏi repo ở commit `ec0db28`. Bản hiện tại khôi
phục từ lịch sử git và sửa các lỗi bên dưới — ghi lại để người đọc biết đâu là
bản gốc, đâu là phần sửa sau.

| Script hiện tại | Bản gốc | Lỗi đã sửa |
| --- | --- | --- |
| `cp2_lineage_trace.py` | `check_lineage.py` | ChromaDB trỏ vào `data/embeddings` thay vì `data/chroma` nên tầng index luôn báo lỗi kết nối; thêm tầng raw response (bản gốc chỉ có raw records → clean → index) |
| `cp2_source_attribution.py` | `source_attribution.py` | Chỉ đọc tầng clean nên không phân biệt được lỗi do parse hay do cleaning; thêm đối chiếu raw ↔ clean |
| `cp3_verify_raw.py` | `P2_cp3_task1_verify.py` | Cộng dồn `len()` của mọi `*.json` trong `data/raw` — ra số đúng chỉ do may (raw response là dict nên `.get("items")` trả rỗng); thêm ghi vân tay sha256 |
| `cp3_compare_counts.py` | `P2_cp3_task2_compare.py` | In sẵn 3 lý do chênh lệch bất kể chênh lệch thực tế là bao nhiêu, kể cả khi bằng 0; nay đọc lý do thật từ `cleaning_report.json` và đối chiếu theo `paper_id` |
| `cp3_no_refetch_audit.py` | `P2_cp3_task3_check.py` | **Lỗi nặng nhất**: quét `Path(".").glob("*.py")` — chỉ file `.py` ở thư mục gốc, mà code thật nằm trong `src/`, nên phép quét không nhìn thấy gì và luôn in "không phát hiện gọi mạng". Nay quét `src/`, và vì `crossref.py` buộc phải có `requests.get`, kiểm tra chuyển sang xác minh guard `refresh_source` + vân tay snapshot |
| `cp5_pre_corruption_check.py` | `cp5_validation.py` | Kiểm tra "raw nguyên vẹn" bằng `dir.exists()` (thư mục rỗng vẫn OK) và chọn mẫu repair bằng `data[0]` — không liên quan tới corruption thật; nay so sha256 và đọc `corruption_log.json` |
| `cp6_repair_lineage_proof.py` | *(mới)* | CP6 trước đây không có script nào. Đây là phần chứng minh phục hồi ở mức từng bản ghi |

Điểm chung của các lỗi trên: kiểm tra **không bao giờ đỏ được**. Một check luôn
xanh không chứng minh hệ thống đúng, nó chỉ che mất chỗ cần nhìn — và tôi đã in
"[OK] Tuyệt vời! Không phát hiện lệnh gọi mạng nào" trong khi phép quét không hề
đọc file nào.

## Giới hạn đã biết

`cp2_lineage_trace.py` báo `[SKIP]` ở tầng index trên bản clone sạch:
`data/chroma/chroma.sqlite3` nằm trong `.gitignore` nên collection metadata không
theo repo, trong khi 21 file `.bin` của HNSW **lại được commit**. Các file `.bin`
đó là mồ côi — không có sqlite thì không load được. Chạy `run_phase1.py` sẽ dựng
lại index và script báo OK. Đây là phạm vi Vai trò 4, tôi chỉ ghi nhận.
