# Phase 2 — Báo cáo hỏng dữ liệu, quan sát và khả năng phục hồi

Thời điểm tạo: 2026-08-06T20:48:09.528092+00:00

## 1. Tóm tắt

Báo cáo đo tác động của việc hỏng dữ liệu lên chất lượng RAG agent và kiểm chứng mức phục hồi sau khi chạy lại quy trình làm sạch từ dữ liệu thô. Cả ba trạng thái dùng **cùng một test set đã khoá**, cùng evaluator và cùng `top_k`; nếu không, phần chênh lệch sẽ phản ánh việc đổi đề bài chứ không phải tác động của dữ liệu.

---

## 2. So sánh chỉ số

| Nhóm | Chỉ số | Baseline | Corrupted | Repaired | Δ do hỏng dữ liệu | Δ sau sửa chữa | Trạng thái |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Retrieval | Tỉ lệ retrieval trúng | 1.000 | 0.667 | 1.000 | -0.3333 | 0 | Suy giảm → phục hồi hoàn toàn |
| Tương đồng | Token F1 trung bình | 1.000 | 0.723 | 1.000 | -0.2769 | 0 | Suy giảm → phục hồi hoàn toàn |
| LLM judge | Độ chính xác theo judge | 1.000 | 0.708 | 1.000 | -0.2917 | 0 | Suy giảm → phục hồi hoàn toàn |
| LLM judge | Điểm judge trung bình | 5 | 4 | 5 | -1.00 | 0 | Suy giảm → phục hồi hoàn toàn |
| Observability | Chất lượng dữ liệu | ĐẠT | **KHÔNG ĐẠT** | ĐẠT | - | - | 11/11 → 6/11 → 11/11 |
| Observability | Độ tươi mới | CÒN MỚI | QUÁ HẠN | CÒN MỚI | - | - | số dòng quá hạn: 0 → 1 → 0 |

### Chỉ số Ragas

| Chỉ số | Baseline | Corrupted | Repaired | Δ do hỏng dữ liệu | Δ sau sửa chữa | Ghi chú |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Mức liên quan của câu trả lời | 0.184 | 0.137 | 0.182 | -0.0467 | -0.0026 |  |
| Độ chính xác ngữ cảnh | 0.750 | 0.542 | 0.750 | -0.2083 | 0 |  |
| Độ bao phủ ngữ cảnh | 0.750 | 0.667 | 0.750 | -0.0833 | 0 |  |
| Mức trung thành với ngữ cảnh | 0.729 | 0.558 | 0.708 | -0.1712 | -0.0208 | mẫu số lệch: 24 / 23 / 24 |

> Chỉ số nào có mẫu số lệch giữa ba trạng thái thì không so sánh trực tiếp được — phần chênh lệch có thể chỉ do số mẫu bị loại khác nhau.

---

## 3. Mức phục hồi

Bốn chỉ số chính (retrieval, token F1, judge) ở trạng thái repaired đều trở lại đúng bằng baseline (Δ = 0).

Kết quả này là kỳ vọng được chứ không phải may mắn: raw snapshot còn nguyên và cleaning là hàm thuần, nên làm sạch lại từ raw bắt buộc phải cho ra đúng dataset ban đầu. Nếu Δ ≠ 0 thì mới là dấu hiệu cleaning không tái lập được.

Riêng các chỉ số Ragas **chưa** khớp lại với baseline:

- `answer_relevancy`: repaired 0.1816 so với baseline 0.1841 (-0.0026)
- `faithfulness`: repaired 0.7083 so với baseline 0.7292 (-0.0208)

Cần đọc phần này thận trọng. Baseline và repaired được sinh từ cùng một dataset nên câu trả lời giống hệt nhau; mọi chênh lệch còn lại đến từ tầng LLM bên trong Ragas chứ không phải từ pipeline. Đây là **thước đo sàn nhiễu**: thay đổi nhỏ hơn mức chênh lệch này ở các lần đo khác đều không kết luận được điều gì.

---

## 4. Bằng chứng và giới hạn

- Mọi con số đọc từ `baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json` và các file quality/freshness tương ứng; report không tự tính lại.
- Chuỗi nhân quả đầy đủ cần đối chiếu thêm `corruption_log.json` (loại lỗi, record ID, before/after) và so cùng một `id` giữa `baseline_answers.json` và `corrupted_answers.json`.
- Chỉ số suy giảm chứng minh corruption có tác động; chỉ số **không đổi** không chứng minh hệ thống bền — có thể loại corruption đó chưa chạm tới đường đi retrieval → metadata.

Report do pipeline sinh tự động.