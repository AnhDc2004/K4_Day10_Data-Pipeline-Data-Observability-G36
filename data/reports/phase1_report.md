# Phase 1 — Báo cáo Baseline

Thời điểm tạo: 2026-08-06T20:27:30.325822+00:00

## 1. Nguồn dữ liệu và phạm vi

| Mục | Giá trị |
| --- | --- |
| Nguồn dữ liệu | Crossref REST API |
| Câu truy vấn | agentic retrieval augmented generation large language model |
| Số bản ghi thô | 24 |
| Số bản ghi sau làm sạch | 24 |
| Ngưỡng freshness (ngày) | 180 |

## 2. Chỉ số đánh giá

| Mục | Giá trị |
| --- | --- |
| Số sample | 24 |
| Tỉ lệ retrieval trúng | 1.000 |
| Token F1 trung bình | 1.000 |
| Độ chính xác theo LLM judge | 1.000 |
| Điểm judge trung bình | 5 |

**Chỉ số Ragas**

| Mục | Giá trị |
| --- | --- |
| Tổng số mẫu | 24 |
| Mức liên quan của câu trả lời | 0.184 |
| — số mẫu chấm được | 24 |
| Độ chính xác ngữ cảnh | 0.750 |
| — số mẫu chấm được | 24 |
| Độ bao phủ ngữ cảnh | 0.750 |
| — số mẫu chấm được | 24 |
| Mức trung thành với ngữ cảnh | 0.729 |
| — số mẫu chấm được | 24 |

## 3. Chất lượng dữ liệu

- Kết quả tổng: **ĐẠT** (11/11 check đạt)
- Tổng số dòng: 24
- Report: `data/quality/phase1-baseline_quality.json`

| Check | Kết quả | Quan sát được | Kỳ vọng | Chi tiết |
| --- | --- | --- | --- | --- |
| `row_count_min` | ĐẠT | 24 | >= 10 rows |  |
| `schema_columns_present` | ĐẠT | 8 | 8 cot bat buoc |  |
| `paper_id_not_null` | ĐẠT | 0 | 0 missing |  |
| `paper_id_unique` | ĐẠT | 24 | 24 unique |  |
| `duplicate_records` | ĐẠT | 0 | 0 duplicate rows |  |
| `title_not_null` | ĐẠT | 0 | 0 missing |  |
| `summary_not_null` | ĐẠT | 0 | 0 missing |  |
| `text_for_embedding_not_empty` | ĐẠT | 0 | 0 missing |  |
| `summary_min_chars` | ĐẠT | 0 | 0 row < 100 ky tu |  |
| `published_parseable` | ĐẠT | 0 | 0 row khong parse duoc ngay |  |
| `freshness_age_days` | ĐẠT | 174 | max age_days <= 180, 0 row thieu age_days |  |

## 4. Độ tươi mới của dữ liệu

| Mục | Giá trị |
| --- | --- |
| Ngày xuất bản mới nhất | 2026-08-01 |
| Ngày xuất bản cũ nhất | 2026-02-13 |
| Số dòng quá hạn | 0 |
| Tổng số dòng | 24 |
| Còn tươi mới | có |
| Ngưỡng freshness (ngày) | 180 |
| Tuổi lớn nhất (ngày) | 174 |
| Tuổi nhỏ nhất (ngày) | 5 |
| Tuổi trung bình (ngày) | 76.400 |
| Số dòng thiếu ngày xuất bản | 0 |
| Thời điểm tạo | 2026-08-06T20:25:51.058296+00:00 |
| Đường dẫn report | data/quality/freshness_report.json |

## 5. Bằng chứng và giới hạn

- Chỉ số đọc từ artifact JSON do evaluator ghi ra; report này không tính lại số liệu.
- Cần kiểm tra `judge.reasoning` trong file answers: nếu là fallback heuristic thì `judge_accuracy` không phải LLM judge và không được trình bày như metric thật.
- Test set được khoá và dùng lại nguyên vẹn cho corrupted và repaired.
- Chỉ số Ragas kèm hậu tố `_n` là số mẫu thực sự chấm được; nếu `_n` nhỏ hơn tổng số mẫu thì giá trị trung bình đang tính trên mẫu số nhỏ hơn và không so sánh trực tiếp được.
