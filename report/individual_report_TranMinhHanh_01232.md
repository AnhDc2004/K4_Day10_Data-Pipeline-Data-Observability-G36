# Báo cáo cá nhân — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Trần Minh Hạnh |
| MSSV | 01232 |
| Khóa/Lớp | K4 |
| Nhóm | G36 |
| Vai trò chính | Vai trò 3 — Cleaning & Corruption Owner |
| Phạm vi | Clean schema, corruption và repair |
| Repository | `AnhDc2004/K4_Day10_Data-Pipeline-Data-Observability-G36` |
| Ngày hoàn thành | 2026-08-07 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Cleaning và clean contract | `src/ingestion/cleaning.py` | `list[PaperRecord]`, `run_date` | Clean DataFrame, CSV/JSON, cleaning report | Hoàn thành |
| Corruption có kiểm soát | `src/ingestion/corruption.py` | Baseline clean DataFrame | Corrupted DataFrame và corruption log | Hoàn thành |
| Tạo artifact CP5 | `script/run_corruption_cp5.py` | Baseline clean JSON | Corrupted CSV/JSON | Hoàn thành |
| Repair từ raw | `script/run_repair_cp6.py` | Raw snapshot, baseline và corruption log | Repaired CSV/JSON, quality/freshness và repair validation | Hoàn thành |
| Kiểm thử | `tests/test_cleaning.py`, `tests/test_corruption.py`, `tests/test_repair.py` | Dữ liệu mẫu có kiểm soát | Regression tests | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Kiểm tra clean–index contract | Retrieval/index | Xác minh ID, title và `text_for_embedding` không drift |
| Rà soát paper được chọn vào test set | Evaluation | Sáu paper có đủ field và không còn HTML/JATS markup |
| Kiểm tra metadata JSON | Embedding manifest | Phát hiện `pdf_url: NaN`; phối hợp chuẩn hóa thành chuỗi rỗng |

## 3. Kết quả theo checkpoint

| Checkpoint | Nhiệm vụ | Kết quả và bằng chứng |
| --- | --- | --- |
| CP0 | Chốt clean schema và quy tắc null/date/duplicate/list | `docs/clean-data-contract.md` |
| CP1 | Normalize, parse ngày, dedupe, `age_days`, embedding text | `data/clean/papers_clean.csv`, `papers_clean.json`, `cleaning_report.json` |
| CP2 | Kiểm tra ID/embedding và row test set | 24 ID unique, 0 embedding rỗng, không còn HTML entity/markup |
| CP3 | Kiểm tra schema và quality baseline | 24 rows, `age_days` 5–174, quality 11/11 |
| CP5 | Missing/drop/noise/old-date/duplicate | `corruption_log.json`, corrupted CSV/JSON, 24 → 23 rows |
| CP6 | Repair lại từ raw và xác minh phục hồi | 24 repaired rows, quality 11/11, repair validation PASS |

Artifact tiêu biểu của phần việc là `data/results/repair_validation.json`. Artifact này chứng minh repaired dataset được dựng lại từ raw, phục hồi các record bị drop, sửa missing/noise/old date, loại duplicate và khôi phục schema/ID về trạng thái baseline.

## 4. Giải thích kỹ thuật

### Vấn đề cần giải quyết

Dữ liệu Crossref không đồng nhất về khoảng trắng, HTML/JATS markup, độ chính xác của ngày, danh sách tác giả/chủ đề và giá trị thiếu. Nếu đưa thẳng dữ liệu này vào index, retrieval có thể chứa nội dung rỗng hoặc metadata không hợp lệ. Pipeline còn phải chứng minh được dữ liệu xấu làm thay đổi hệ thống và có thể repair từ nguồn raw đáng tin cậy.

### Cách triển khai cleaning

- Chuẩn hóa khoảng trắng và giải mã HTML entity.
- Loại JATS/HTML tag trước khi tạo embedding text.
- Loại record thiếu `paper_id` hoặc `title`.
- Chuẩn hóa, bỏ phần tử rỗng và dedupe `authors`/`categories` không phân biệt hoa thường.
- Parse ngày bằng `format="mixed"` để hỗ trợ `YYYY-MM`, `YYYY-MM-DD` và timestamp.
- Dedupe theo stable `paper_id`, giữ record có `updated` mới nhất.
- Tính `age_days` theo `run_date`; ngày tương lai nhận 0, ngày sai nhận `NA`.
- Tạo `text_for_embedding` có nhãn Title, Summary, Authors và Categories.
- Ghi count cho record bị filter, duplicate, ngày sai và summary rỗng.

### Cách triển khai corruption

Corruption được thực hiện trên bản copy để không mutate baseline. Năm scenario deterministic gồm:

1. Bỏ hai record mới nhất.
2. Làm rỗng summary của một record.
3. Chèn marker noise vào một summary.
4. Lùi ngày xuất bản 730 ngày và cập nhật `age_days` tương ứng.
5. Thêm một duplicate có cùng stable ID.

Mỗi operation ghi `type`, `record_ids`, `parameter`, `before_count` và `after_count`. Sau biến đổi, `summary_chars` và `text_for_embedding` được tạo lại để corrupted artifact phản ánh đúng lỗi nguồn.

### Cách triển khai repair

Repair không copy baseline và không sửa tay corrupted JSON. Runner nạp lại `data/raw/crossref_records.json`, gọi lại `build_clean_dataframe()` và dùng đúng baseline run date được suy ra từ `published + age_days`. Cách này làm repair tái lập được ngay cả khi chạy script vào ngày khác.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `PaperRecord`: ID, title, summary, authors, categories, dates và URL |
| Clean output | 16 cột theo `CLEAN_COLUMNS` |
| Trường bắt buộc | `paper_id`, `title`, `text_for_embedding` không rỗng; `paper_id` unique |
| Corrupted output | Dataset riêng và log có thể audit |
| Repaired output | Dataset dựng lại từ raw, schema và ID khớp baseline |
| Module sử dụng output | Retrieval index, evaluation, observability và reporting |
| Lỗi cần xử lý | Null, ngày hỗn hợp/sai, duplicate ID, markup, HTML entity và metadata `NaN` |

### Cách xác minh

```powershell
python -m unittest discover -s tests -v
python script/run_cleaning_cp1.py
python script/run_corruption_cp5.py
python script/run_repair_cp6.py
```

- Kết quả thực tế: 11/11 test đạt.
- Baseline: 24 rows; corrupted: 23 rows; repaired: 24 rows.
- Repaired quality: 11/11 checks pass; freshness PASS.
- Artifact chính: `data/results/corruption_log.json` và `data/results/repair_validation.json`.

## 5. Quyết định kỹ thuật quan trọng

- **Bối cảnh:** Repair cần chứng minh khả năng phục hồi thật, không chỉ làm file repaired giống baseline.
- **Phương án cân nhắc:** copy baseline sang repaired; sửa trực tiếp corrupted rows; hoặc chạy lại cleaning từ raw snapshot.
- **Phương án chọn:** chạy lại toàn bộ cleaning từ raw snapshot.
- **Lý do:** raw là nguồn đáng tin cậy và giữ lineage; cách này tránh che giấu lỗi bằng việc vá kết quả, đồng thời tái lập được pipeline.
- **Bằng chứng:** `repair_validation.json` có toàn bộ check PASS, 24 ID được phục hồi, noise bị loại và duplicate chỉ còn một bản.

## 6. Lỗi hoặc blocker đã xử lý

- **Triệu chứng:** một ngày Crossref dạng `2026-08` bị parse thành `NaT` khi nằm chung Series với ngày đầy đủ.
- **Tái hiện:** chạy cleaning trên tập có đồng thời `YYYY-MM`, `YYYY-MM-DD` và timestamp.
- **Nguyên nhân:** pandas suy luận một format chung cho toàn Series.
- **Cách xử lý:** dùng `pd.to_datetime(..., format="mixed", errors="coerce", utc=True)`.
- **Xác minh:** regression test `test_mixed_crossref_date_precision_is_parsed` đạt; clean artifact có 0 ngày không parse được.
- **Điều học được:** phải kiểm thử dữ liệu nguồn có nhiều độ chính xác thời gian, không chỉ một sample ISO chuẩn.

Một lỗi khác là HTML entity như `R&amp;D` và JATS tag còn trong summary. Cleaning được bổ sung `html.unescape()` và loại markup trước khi tạo embedding text. Regression test xác nhận không còn entity/tag trong output.

## 7. Hiểu biết về luồng end-to-end

1. Crossref response được lưu thành raw snapshot và ánh xạ sang `PaperRecord`. Cleaning chuẩn hóa dữ liệu, tạo các field dẫn xuất và ghi clean artifacts. Retrieval dùng `paper_id` làm identity, `text_for_embedding` làm content và metadata sạch để xây Chroma collection.
2. Evaluation set lấy câu hỏi và ground truth từ clean rows thật. `ground_truth_doc_ids` là stable `paper_id`, giúp kiểm tra tài liệu đúng có xuất hiện trong top-k hay không; answer được so với ground truth bằng token F1 và judge metric.
3. Quality checks kiểm tra completeness, uniqueness, validity và schema tại một trạng thái dữ liệu. Freshness tập trung vào `published`/`age_days`, phát hiện dữ liệu cũ hoặc thiếu timestamp.
4. Baseline, corrupted và repaired phải dùng cùng test set để delta phản ánh thay đổi dữ liệu/index, không phải do đổi câu hỏi hoặc ground truth.
5. Repair thành công khi repaired artifact được tạo từ raw, schema/ID/quality được phục hồi và downstream metrics được đo lại trên cùng test set. Phần dữ liệu của tôi đã PASS; repaired index và evaluation metric thuộc owner RAG/evaluation.

## 8. Phân tích kết quả

### Metrics và tín hiệu hiện có

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.000 | Chưa có artifact | Chưa có artifact | Cần Vai trò 4/5 rebuild và evaluate |
| `mean_token_f1` | 0.750 | Chưa có artifact | Chưa có artifact | Không tự suy diễn metric khi chưa chạy |
| `judge_accuracy` | 1.000 | Chưa có artifact | Chưa có artifact | Baseline artifact có kết quả |
| `mean_judge_score` | 5.000 | Chưa có artifact | Chưa có artifact | Ragas baseline có lỗi riêng |
| Quality checks | 11/11 PASS | Chưa có quality artifact | 11/11 PASS | Repaired quality đã phục hồi baseline |
| Freshness | PASS | Chưa có freshness artifact | PASS | Repaired max `age_days` = 174 |
| Row count | 24 | 23 | 24 | Hai row bị drop, một duplicate được thêm, repair phục hồi 24 |

### Chuỗi nguyên nhân–bằng chứng

1. Drop/missing/noise/old date/duplicate → corrupted dataset khác baseline và row count còn 23 → cần downstream quality/evaluation chạy để đo tác động metric.
2. Nạp lại raw và chạy cleaning → khôi phục 24 unique IDs, summary, ngày và embedding text → repaired quality đạt 11/11 và freshness PASS.

Corruption có bằng chứng rõ nhất ở tầng dữ liệu là `drop_latest`, vì hai paper biến mất hoàn toàn và có thể làm ground-truth document không còn trong index. Tuy nhiên, chưa kết luận mức giảm retrieval metric cho đến khi corrupted index và evaluation artifacts được tạo.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng

1. Raw snapshot và stable ID là nền tảng để repair có thể kiểm chứng và tái lập.
2. Quality report phải được tính từ artifact thật; file tồn tại không đồng nghĩa dữ liệu đạt contract.
3. Lỗi nhỏ như HTML entity, mixed date hoặc `NaN` metadata có thể lan từ cleaning sang index, test set và agent output.

### Nếu có thêm thời gian

Tôi sẽ bổ sung property-based tests tạo nhiều biến thể null/date/markup và đo hash lineage raw–clean–repaired. Tiêu chí cải thiện là mọi input hợp lệ giữ stable ID, mọi output tuân thủ strict JSON và repaired hash khớp clean baseline khi dùng cùng raw snapshot/run date.

## 10. Cam kết của thành viên

- [x] Nội dung phản ánh đúng phạm vi và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module phụ trách.
- [x] Kết luận có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi thành công cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo không sao chép nguyên văn báo cáo nhóm hoặc thành viên khác.

**Họ và tên:** Trần Minh Hạnh  
**Ngày xác nhận:** 2026-08-06
