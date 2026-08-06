# CP1 — Vai trò 5: Evaluation & Observability

> Checkpoint 1 · 00:30–01:05 · Nhóm 5 người
> Tiếp nối [cp0_eval_observability_contract.md](cp0_eval_observability_contract.md)
> Trạng thái: **quality + freshness đã implement và chạy trên clean data thật**; test set **chưa ghi file** (đúng yêu cầu CP1: chờ `paper_id` ổn định) và đang **bị block bởi chất lượng dữ liệu upstream**.

---

## 1. Đã implement

| File | Hàm | Nội dung |
| --- | --- | --- |
| `src/observability/quality.py` | `run_data_quality_checks(df, settings, report_name)` | 10 check, ghi `data/quality/<report_name>_quality.json` |
| `src/observability/quality.py` | `build_freshness_report(df, settings, report_path)` | freshness từ `published` + `age_days`, ghi JSON theo path truyền vào |
| `src/evaluation/testset.py` | `paper_rejection_reason(row)` | luật loại paper không dùng làm sample |
| `src/evaluation/testset.py` | `select_representative_papers(df, limit)` | chọn paper đại diện + log lý do loại từng row |
| `src/evaluation/testset.py` | `draft_questions(row)` | sinh 4 sample summary/authors/date/categories đúng schema `metrics.py` |
| `src/evaluation/testset.py` | `build_test_set(df, output_path)` | **để lại cho CP2** (ghi file khi `paper_id` đã ổn định) |

Hai quyết định thiết kế đáng nêu:

1. **Check fail không raise.** Pipeline vẫn chạy tiếp, vì mục tiêu của lab là *đo* impact của data xấu lên metric — raise sẽ làm mất luôn số liệu cần so sánh.
2. **Không tính lại tuổi bằng `datetime.now()`.** `build_freshness_report` chỉ đọc `age_days` do cleaning tính từ `run_date`. Nếu tính lại, chạy lại vào ngày khác sẽ ra số khác và baseline không tái lập được.
3. **Cột thiếu → check fail kèm `details`, không `KeyError`.** Cleaning còn đang thay đổi; quality module phải sống sót để báo cáo được vấn đề thay vì crash.

### Thay đổi so với contract CP0

CP0 chốt 7 check, CP1 implement **10** — thêm 3 check theo đúng yêu cầu CP1 ("row count, paper_id unique, title/summary missing và duplicate"):

- `schema_columns_present` — bắt lỗi contract clean ↔ index sớm.
- `summary_not_null` — tách "thiếu hẳn" khỏi "quá ngắn" (`summary_min_chars`), vì hai lỗi này đến từ hai nguyên nhân khác nhau.
- `duplicate_records` — trùng trên `(paper_id, title, published)`, bổ sung cho `paper_id_unique` để CP5 bắt được corruption "add duplicate rows".

---

## 2. Quality report đầu tiên (evidence baseline)

Nguồn: `data/clean/papers_clean.csv` (5 rows) · Artifact: `data/quality/baseline_quality.json`

**Kết quả: 6/10 pass — `success: false`**

| Check | Kết quả | Observed | Chi tiết |
| --- | --- | --- | --- |
| `row_count_min` | ❌ FAIL | 5 | cần ≥ 10 |
| `schema_columns_present` | ✅ PASS | 8/8 | đủ cột contract CP0 §4 |
| `paper_id_not_null` | ✅ PASS | 0 missing | |
| `paper_id_unique` | ✅ PASS | 5 unique | |
| `duplicate_records` | ✅ PASS | 0 | |
| `title_not_null` | ✅ PASS | 0 missing | |
| `summary_not_null` | ❌ FAIL | 3 missing | 3/5 row không có summary |
| `text_for_embedding_not_empty` | ✅ PASS | 0 | |
| `summary_min_chars` | ❌ FAIL | 3 | 3/5 row < 100 ký tự |
| `freshness_age_days` | ❌ FAIL | max 5530 | 5/5 row stale (> 180 ngày) |

### Freshness report — `data/quality/freshness_report.json`

| Field | Giá trị |
| --- | --- |
| `latest_published` | 2022-03-21 |
| `oldest_published` | 2011-06-16 |
| `stale_rows` / `total_rows` | 5 / 5 |
| `is_fresh` | **false** |
| `max_age_days` / `mean_age_days` | 5530 / 3316.2 |
| `missing_published` | 0 |

---

## 3. Draft test set — chọn paper & câu hỏi

Chạy `select_representative_papers(df)`: **chỉ 2/5 paper dùng được**, cần tối thiểu 6.

| paper_id | Kết quả | Lý do |
| --- | --- | --- |
| `10.1093/oso/9780190941659.003.0001` | ✅ chọn | Why Use Automated Machine Learning? |
| `10.1093/oso/9780198828044.003.0003` | ✅ chọn | Machine learning with sklearn |
| `10.1002/9781119902881` | ❌ loại | `missing_summary` |
| `10.1017/cbo9780511804779.017` | ❌ loại | `missing_summary` |
| `10.1017/cbo9780511975509.007` | ❌ loại | `missing_summary` |

Draft 4 câu hỏi (đã verify sinh ra đúng, cụm khóa khớp `_extract_answer`):

```
[summary]    What is the paper 'Why Use Automated Machine Learning?' about?
             GT: "Machine learning is involved in search, translation, detecting depression, ..."
[authors]    Who authored the paper 'Why Use Automated Machine Learning?'?
             GT: "Kai R. Larsen, Daniel S. Becker"
[date]       When was the paper 'Why Use Automated Machine Learning?' published?
             GT: "2021-07-29 00:00:00+00:00"
[categories] What categories does the paper 'Why Use Automated Machine Learning?' belong to?
             GT: "Uncategorized"
ground_truth_doc_ids: ["10.1093/oso/9780190941659.003.0001"]  ← lấy trực tiếp từ cột paper_id
```

**Chưa ghi `data/eval/test_set.json`** — đúng yêu cầu CP1 và vì 2 paper là không đủ để metric có ý nghĩa.

---

## 4. Blocker gửi các vai trò khác (có bằng chứng)

### B1 — Ingestion không dùng `settings.source_query` / `source_filter` / `max_results` (vai trò 2) — **nghiêm trọng nhất**

Bằng chứng từ chính raw response (`data/raw/crossref_raw_response.json`):

```
message.query = {"start-index": 0, "search-terms": "machine learning"}
items-per-page = 5      →  settings.max_results = 24
```

Trong khi `core/config.py:127-129` quy định:

```
source_query  = "agentic retrieval augmented generation large language model"
source_filter = "from-pub-date:2026-02-07,has-abstract:true"
```

Hệ quả dây chuyền — **cả 4 check FAIL ở §2 đều quy về đây**, không phải lỗi cleaning:

- không có `rows=24` → 5 row → `row_count_min` fail;
- không có `has-abstract:true` → 3/5 item **không có field `abstract` ngay trong raw payload** (đã kiểm tra từng item) → `summary_not_null` + `summary_min_chars` fail;
- không có `from-pub-date` → toàn sách/chương xuất bản 2011–2022 → `freshness_age_days` fail, `is_fresh=false`, `stale_rows=5/5`.

Cần: gọi lại Crossref với đúng `params` từ `Settings` (`query`, `filter`, `rows`).

### B2 — Tên file raw không khớp `Settings` (vai trò 2 / vai trò 1)

`settings.paths.raw_api_response` = `data/raw/crossref_response.json` → **không tồn tại**; file thực tế là `data/raw/crossref_raw_response.json`. `phase1.py` load theo Settings sẽ miss. (`crossref_records.json` thì khớp.)

### B3 — `published` chưa chuẩn hoá về `YYYY-MM-DD` (vai trò 3)

Giá trị hiện tại: `2021-07-29 00:00:00+00:00`. Vì `_extract_answer` trả về **nguyên văn** `metadata["published"]`, ground truth loại `date` sẽ mang cả `00:00:00+00:00`. Token F1 vẫn khớp (GT copy cùng chuỗi) nhưng answer đọc rất xấu khi demo và làm nhiễu LLM judge. Đề nghị cleaning ghi `published` dạng `YYYY-MM-DD`.

### B4 — `categories_joined` = `"Uncategorized"` cho **100%** rows → câu hỏi `categories` bị vô hiệu

Đã kiểm tra tận nguồn: **mọi item Crossref đều không có field `subject`** → đây là giới hạn của source, không phải lỗi parse.

Rủi ro đo lường phải nói rõ: nếu mọi paper cùng ground truth `"Uncategorized"` thì `token_f1` của loại `categories` **luôn = 1.0 bất kể retrieval trúng paper nào** → `mean_token_f1` bị thổi phồng và loại câu hỏi này **không phản ứng với corruption**. 

Phương án ở CP2 (chọn khi biết dữ liệu mới sau khi B1 được sửa):
- nếu dữ liệu mới có `subject` → giữ nguyên 4 loại;
- nếu vẫn `Uncategorized` toàn bộ → vẫn giữ loại `categories` cho đủ 4 loại theo yêu cầu lab, nhưng **báo cáo metric tách theo `question_type`** và ghi rõ loại này không mang tín hiệu.

---

## 5. Tự kiểm CP1

- [x] Implement check row count, `paper_id` unique, title/summary missing, duplicate → 10 check chạy thật.
- [x] Freshness lấy từ `published`/`age_days`, không dùng ngày hiện tại giả định.
- [x] Ghi quality report đầu tiên làm evidence baseline → `data/quality/baseline_quality.json`, `data/quality/freshness_report.json`.
- [x] Chọn paper đại diện **từ cleaned dataframe** (không dùng raw chưa clean) + log lý do loại.
- [x] Draft question/ground truth kiểm chứng được bằng nội dung paper.
- [x] Chưa ghi test set — chờ `paper_id` ổn định (và chờ B1).
- [ ] **Blocked**: cần B1 được sửa để có ≥ 6 paper hợp lệ trước khi khoá test set ở CP2.

---

## 6. Re-check sau khi vai trò 2 refresh dữ liệu (cùng phiên CP1)

Dữ liệu mới: **24 rows** (đúng `max_results`), query/filter đã áp dụng.

| Blocker | Trạng thái | Bằng chứng |
| --- | --- | --- |
| B1 — ingestion không dùng `Settings` | ✅ **Đã sửa** | 24 rows, `oldest_published = 2026-02-13` ≈ đúng `from-pub-date:2026-02-07`, `summary_not_null` PASS 0 missing |
| B2 — tên file raw sai | ✅ **Đã sửa** | `data/raw/crossref_response.json` đã tồn tại |
| B3 — `published` chưa chuẩn hoá | ❌ **Chưa sửa** | vẫn là `2026-08-01 00:00:00+00:00` |
| B4 — `categories_joined` toàn `Uncategorized` | ❌ Không sửa được | giới hạn source: Crossref không trả `subject` |
| **B5 — partial date → NaN** | 🆕 **Mới phát hiện** | xem dưới |

### Quality baseline lần 2 — **9/11 pass**

Artifact đã ghi đè bằng số liệu mới: `data/quality/baseline_quality.json`, `data/quality/freshness_report.json`.

| Check | Kết quả | Observed |
| --- | --- | --- |
| `row_count_min` | ✅ | 24 |
| `summary_not_null` / `summary_min_chars` | ✅ / ✅ | 0 / 0 |
| `paper_id_unique` / `duplicate_records` | ✅ / ✅ | 24 unique / 0 |
| `published_parseable` | ❌ | 2 row không parse được |
| `freshness_age_days` | ❌ | max 174 (≤180 ✅) nhưng **2 row thiếu `age_days`** |

Freshness: `is_fresh=false`, `stale_rows=0/24`, `missing_published=2`, latest `2026-08-01`, max_age `174`.

### Lỗ hổng trong chính bộ check của tôi (đã vá trong CP1)

Lần chạy đầu sau refresh cho **10/10 PASS nhưng `is_fresh=false`** — mâu thuẫn. Nguyên nhân: `NaN > threshold` trong pandas luôn là `False`, nên 2 row thiếu `age_days` **lọt qua `freshness_age_days` một cách im lặng**, và không có check nào soi cột `published`. Đã sửa:

- thêm check **`published_parseable`** (11 check, trước là 10);
- `freshness_age_days` nay đếm riêng `missing_age` và fail nếu > 0.

Đây đúng là loại lỗi mà lab muốn dạy: *check pass không có nghĩa là data sạch, nếu check không nhìn đúng chỗ.*

### B5 — Partial date từ Crossref bị mất im lặng (vai trò 2 + vai trò 3)

Hai row hỏng: `10.1111/exsy.70341`, `10.21079/11681/50309` → `published` = `NaN`, `age_days` = `NaN`.

Truy ngược raw records: giá trị là `"2026-08"` và `"2026-07"` — **partial date chỉ có năm-tháng**, cleaning parse không ra nên thành `NaN` nhưng **vẫn giữ row lại**.

Truy tiếp vào raw payload của `10.1111/exsy.70341`:

```
issued            : {"date-parts": [[2026, 6, 30]]}   ← đầy đủ
published         : {"date-parts": [[2026, 6, 30]]}   ← đầy đủ
published-print   : {"date-parts": [[2026, 8]]}       ← partial, và đây là cái đang được dùng
```

Nên có 2 việc:

- **Vai trò 2:** ưu tiên `issued` → `published` → `published-online`, chỉ dùng `published-print` khi không còn lựa chọn (hoặc chọn `date-parts` dài nhất). Riêng DOI này sẽ ra `2026-06-30` thay vì `2026-08`.
- **Vai trò 3:** partial date `YYYY-MM` → pad thành ngày 01 thay vì để `NaN`; nếu vẫn không parse được thì **drop row + ghi log**, không giữ `NaN` im lặng.

### Test set — **đã hết block**

`select_representative_papers` cho **6/6 paper hợp lệ** (chỉ loại đúng 2 row `missing_published` ở B5) → sẽ sinh **24 sample** (6 paper × 4 loại), đủ điều kiện khoá test set ở CP2. Không cần dùng phương án dự phòng bên dưới.

---

## 7. Re-check lần 3 — sau commit `cp1 - 3 - v2` (cleaning fix)

**Quality baseline: 11/11 PASS · `success: true` · `is_fresh: true`**

| Signal | Giá trị |
| --- | --- |
| `total_rows` | 24 |
| `published_parseable` | 0 row lỗi (trước: 2) |
| `freshness_age_days` | max 174 ≤ 180, 0 row thiếu `age_days` |
| `stale_rows` / `missing_published` | 0 / 0 |
| `latest_published` / `oldest_published` | 2026-08-01 / 2026-02-13 |
| Test set candidates | **6/6**, 0 row bị loại → **24 sample** |

B5 đã được xử lý ở phía **cleaning**: partial date `2026-08` → `2026-08-01`, `2026-07` → `2026-07-01` (`invalid_published_dates: 0`, `output_records: 24`). Raw records **không đổi** — vai trò 2 vẫn giữ nguyên thứ tự ưu tiên field ngày.

### Hai ghi chú độ chính xác (không block CP2)

1. **`10.1111/exsy.70341` có `published = 2026-08-01` trong khi raw payload có `issued`/`published` = `2026-06-30`.** Ingestion lấy `published-print` (`[2026, 8]`) rồi cleaning pad thành ngày 01, lệch ~1 tháng so với ngày công bố thật. Metric **không bị ảnh hưởng** vì ground truth và answer cùng đọc một giá trị metadata, nhưng câu trả lời là sai so với nguồn — nếu còn thời gian, vai trò 2 nên đổi ưu tiên sang `issued`.
2. **B3 vẫn chưa sửa**: `published` còn dạng `2026-08-01 00:00:00+00:00`. Không block, nhưng ground truth loại `date` sẽ mang cả `00:00:00+00:00` khi demo.

**Kết luận: mọi điều kiện đầu vào cho CP2 đã đủ** — có thể implement `build_test_set` và khoá `data/eval/test_set.json` với 24 sample.

### Nếu B1 không kịp sửa (không còn áp dụng — giữ lại làm ghi chép)

Phương án dự phòng để CP2/CP3 vẫn có số liệu: hạ `MIN_PAPERS` xuống 2 và ghi test set 8 sample từ 2 paper hợp lệ, **kèm ghi chú rõ trong report** rằng mẫu quá nhỏ nên mỗi sample sai làm metric đổi 12.5% — kết luận về corruption phải thận trọng tương ứng. Không dùng phương án này nếu B1 kịp sửa.
