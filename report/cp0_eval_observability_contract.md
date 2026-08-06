# CP0 — Vai trò 5: Evaluation & Observability (contract & design)

> Checkpoint 0 · 00:00–00:30 · Nhóm 5 người
> Phạm vi sở hữu: `src/evaluation/testset.py`, `src/observability/quality.py`, `src/observability/reporting.py`
> Artifact bàn giao cuối lab: `data/eval/test_set.json`, `data/quality/*`, `data/reports/*`
> Trạng thái CP0: **thiết kế & chốt contract, chưa implement** (implement ở CP1–CP3).

---

## 0. Tóm tắt: tôi nhận gì, tôi giao gì

| Chiều | Đối tác | Nội dung |
| --- | --- | --- |
| Nhận vào | Vai trò 3 (cleaning) | `cleaned dataframe` + `data/clean/papers_clean.csv|json` với đủ cột ở §4 |
| Nhận vào | Vai trò 4 (RAG) | `LocalEmbeddingIndex` đã build từ đúng cleaned dataframe đó |
| Giao ra | Vai trò 4 + 1 | `data/eval/test_set.json` (khóa cứng, dùng lại cho cả 3 trạng thái) |
| Giao ra | Vai trò 1 (integrator) | `run_data_quality_checks()`, `build_freshness_report()`, `generate_phase1_report()`, `generate_corruption_report()` để gọi trong `phase1.py` / `corruption_flow.py` |
| Giao ra | Cả nhóm | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` |

---

## 1. Việc CP0 #1 — Đọc `testset.py`, `qa.py`, `metrics.py`: format answer & metric

### 1.1 Schema test set — do `metrics.py` quy định, không phải tôigit  tự chọn

`evaluate_pipeline()` đọc test set và truy cập trực tiếp các key sau (`src/evaluation/metrics.py:110-131`). Thiếu key nào là `KeyError` ngay, không có default:

| Key | Kiểu | Dùng ở đâu |
| --- | --- | --- |
| `id` | `str` | ghi vào answers |
| `question_type` | `str` | ghi vào answers, dùng để nhóm metric theo loại |
| `question` | `str` | truyền vào `answer_question()` và vào prompt của judge |
| `ground_truth` | `str` | so với answer bằng `_token_f1` + judge |
| `ground_truth_doc_ids` | `list[str]` | tính `retrieval_hit` |

→ `build_test_set(df, output_path)` phải ghi ra **list các dict đúng 5 key này**, bằng `write_json` (`core/utils.py:14`, đã tự tạo thư mục cha).

### 1.2 Answer được sinh ra thế nào — quyết định cách viết câu hỏi

`answer_question()` (`src/retrieval/qa.py:32-56`) làm 3 việc:

1. **Exact lookup**: `re.search(r"'([^']+)'", question)` — nếu câu hỏi có chuỗi trong **dấu nháy đơn**, chuỗi đó được `index.lookup()` theo `paper_id` hoặc `title` (`retrieval/index.py:168-174`), và document đó được **đẩy lên vị trí đầu** danh sách retrieved.
2. **Semantic search** top-k (`settings.top_k = 4`, `core/config.py:63`).
3. **Trích answer** từ `retrieved[0].metadata` bằng `_extract_answer()` — đây là một bộ luật **khớp chuỗi trên câu hỏi viết thường**:

| Điều kiện trong `question.lower()` | Answer trả về | Nguồn (cột clean) |
| --- | --- | --- |
| chứa `"who authored"` hoặc `"list the authors"` | `metadata["authors_joined"]` | `authors_joined` |
| chứa `"when was"` / `"publication date"` / `"published on"` | `metadata["published"]` | `published` |
| chứa `"what categories"` | `metadata["categories_joined"]` | `categories_joined` |
| còn lại (mặc định) | `first_sentence(metadata["summary"])` | câu đầu của `summary` |

**Hệ quả bắt buộc:** câu hỏi phải chứa đúng cụm khóa ở trên bằng **tiếng Anh**, nếu không mọi câu hỏi đều rơi vào nhánh mặc định (trả về câu đầu summary) và ground truth authors/date/categories sẽ luôn sai → metric tụt vì lỗi thiết kế test set chứ không phải vì data.

### 1.3 Metric được tính thế nào

| Metric | Công thức thật trong code | Ghi chú |
| --- | --- | --- |
| `retrieval_hit_rate` | tỉ lệ item có `any(doc_id in ground_truth_doc_ids for doc_id in retrieved_doc_ids)` (`metrics.py:116`) | hit ở **bất kỳ** vị trí nào trong top-4, không phải hit@1 |
| `mean_token_f1` | F1 trên **tập token** (set, không đếm lặp), lowercase, chuẩn hóa whitespace (`metrics.py:33-45`) | ground truth càng ngắn/đúng nguyên văn cột nguồn thì F1 càng cao |
| `judge_accuracy` | tỉ lệ `judge.correct == True` | LLM judge, structured output `JudgeVerdict` |
| `mean_judge_score` | trung bình `score` 1–5 | |
| `ragas` | mặc định bị skip, chỉ chạy khi `RUN_RAGAS=1` (`metrics.py:74`) | tốn thời gian + quota, CP3 không bật |

### 1.4 Ba cái bẫy tôi phải canh (ghi lại để báo cáo trung thực)

1. **Judge có fallback im lặng** (`metrics.py:61-70`): nếu LLM lỗi/hết quota, judge tự chuyển sang heuristic dựa trên `token_f1` và vẫn trả về `correct=True/False` bình thường. Khi đó `judge_accuracy` **không còn là LLM-judge**. → Ở CP3/CP5 tôi phải mở `*_answers.json` kiểm tra `judge.reasoning`; nếu thấy chuỗi `"Fallback heuristic judge used"` thì báo cáo phải nói rõ, không được trình bày như judge thật.
2. **Regex nháy đơn dễ vỡ**: title chứa dấu `'` (vd `"Don't"`) sẽ làm `re.search(r"'([^']+)'")` bắt sai đoạn. → Khi chọn paper cho test set, **loại bỏ title có dấu nháy đơn**.
3. **`write_json` dùng `ensure_ascii=True`** (`core/utils.py:16`): tên tác giả có dấu sẽ bị escape `\uXXXX` trong file. Đó là escape hợp lệ, `read_json` đọc lại vẫn đúng — không được "sửa tay" file JSON vì tưởng hỏng.

---

## 2. Việc CP0 #2 — Thiết kế 4 loại câu hỏi từ dữ liệu thật

Nguyên tắc: **ground_truth phải copy đúng giá trị cột nguồn của chính row đó**, vì `_extract_answer` trả về nguyên văn giá trị metadata. Không diễn giải lại, không viết câu văn.

Với mỗi paper được chọn (title = `T`, paper_id = `P`):

| `question_type` | Mẫu câu hỏi (giữ nguyên cụm khóa tiếng Anh) | `ground_truth` | `id` |
| --- | --- | --- | --- |
| `summary` | `What is the paper 'T' about?` | `first_sentence(row.summary)` | `{P}::summary` |
| `authors` | `Who authored the paper 'T'?` | `row.authors_joined` | `{P}::authors` |
| `date` | `When was the paper 'T' published?` | `row.published` | `{P}::date` |
| `categories` | `What categories does the paper 'T' belong to?` | `row.categories_joined` | `{P}::categories` |

Ràng buộc khi chọn paper (kiểm tra trước khi ghi file):

- Tối thiểu **6 paper × 4 câu = 24 sample**; nếu `len(df) < 6` thì raise lỗi rõ ràng thay vì im lặng tạo test set bé.
- Loại paper có: `title` rỗng/chứa `'`, `summary` rỗng hoặc quá ngắn, `authors_joined` rỗng, `categories_joined` rỗng, `published` rỗng.
- Ưu tiên title **khác biệt nhau** (không cùng prefix) để `lookup` theo title không mơ hồ.
- Test set được **ghi một lần và khóa lại**; `settings.refresh_test_set` (`config.py:133`) mặc định `False`, nên `phase1.py` phải load lại file cũ nếu đã tồn tại. Corrupted/repaired dùng **đúng file này**, không sinh lại — nếu sinh lại thì so sánh 3 trạng thái mất công bằng.

---

## 3. Việc CP0 #3 — `ground_truth_doc_ids` lấy từ đâu

- `ground_truth_doc_ids = [row.paper_id]` — lấy **trực tiếp từ cột `paper_id` của cleaned dataframe**, tuyệt đối không tự sinh ID, không dùng index dòng, không dùng DOI viết lại.
- Lý do phải khớp tuyệt đối: `retrieval_hit` so `metadata["paper_id"]` (`index.py:159`) với list này bằng so sánh chuỗi **có phân biệt hoa/thường**. `lookup()` có `.lower()` nhưng `retrieval_hit` thì **không** → `paper_id` phải được cleaning ghi ở **một dạng chuẩn duy nhất** (đề nghị: DOI lowercase, không có prefix `https://doi.org/`).
- Kiểm tra bắt buộc trước khi coi test set là xong: mọi `ground_truth_doc_ids[0]` phải tìm được bằng `index.lookup(paper_id)`. Nếu miss → lỗi contract giữa clean và index, phải sửa contract, **không** sửa test set cho khớp.

---

## 4. Contract đầu vào tôi cần (blocking dependency — gửi vai trò 3)

Cleaned dataframe phải có đủ các cột sau. Đây là hợp của cột `index.py:53-63` cần và cột tôi cần:

| Cột | Ai cần | Dùng làm gì |
| --- | --- | --- |
| `paper_id` | index + testset + quality | ID ổn định, ground truth doc id, check unique |
| `title` | index + testset | câu hỏi + exact lookup |
| `summary` | index + testset + quality | ground truth `summary`, check độ dài |
| `authors_joined` | index + testset | ground truth `authors` (chuỗi đã join, không phải list) |
| `categories_joined` | index + testset | ground truth `categories` |
| `published` | index + testset + freshness | ground truth `date` (chuỗi ISO `YYYY-MM-DD`) |
| `age_days` | quality + freshness | tín hiệu freshness |
| `text_for_embedding` | index | nội dung embed |
| `abs_url`, `pdf_url` | index | metadata |
| `summary_chars` | quality | check độ dài (nếu không có thì tôi tự tính từ `summary`) |

Lưu ý gửi vai trò 3: Chroma metadata chỉ nhận **scalar** → `authors`/`categories` dạng list không được đưa vào metadata, phải là `*_joined` dạng string.

---

## 5. Việc CP0 #4 — Danh sách artifact phải có

### 5.1 Sau baseline (`script/run_phase1.py`)

| Artifact | Path (từ `core/config.py`) | Chủ sở hữu |
| --- | --- | --- |
| Raw response | `data/raw/crossref_response.json` | VT2 |
| Raw records | `data/raw/crossref_records.json` | VT2 |
| Clean CSV/JSON | `data/clean/papers_clean.csv` / `.json` | VT3 |
| Embedding manifest | `data/embeddings/papers_embeddings.json` | VT4 |
| Chroma collection | `data/chroma/` — `papers-baseline` | VT4 |
| **Test set** | `data/eval/test_set.json` | **tôi** |
| **Baseline metrics** | `data/results/baseline_metrics.json` | **tôi** |
| **Baseline answers** | `data/results/baseline_answers.json` | **tôi** |
| Agent demo answers | `data/results/agent_demo_answers.json` | VT4/VT1 |
| **Quality report** | `data/quality/<name>_quality.json` | **tôi** |
| **Freshness report** | `data/quality/freshness_report.json` | **tôi** |
| **Phase-1 report** | `data/reports/phase1_report.md` | **tôi** |

### 5.2 Sau corruption flow (`script/run_corruption_flow.py`)

| Artifact | Path |
| --- | --- |
| Corruption log | `data/results/corruption_log.json` |
| Corrupted clean data | `data/clean/papers_clean_corrupted.csv` / `.json` |
| Corrupted embeddings | `data/embeddings/papers_embeddings_corrupted.json` → collection `papers-corrupted` |
| **Corrupted metrics/answers** | `data/results/corrupted_metrics.json` / `corrupted_answers.json` |
| Repaired clean data | `data/clean/papers_clean_repaired.csv` / `.json` |
| Repaired embeddings | `data/embeddings/papers_embeddings_repaired.json` → collection `papers-repaired` |
| **Repaired metrics/answers** | `data/results/repaired_metrics.json` / `repaired_answers.json` |
| **Comparison report** | `data/reports/corruption_report.md` |

### 5.3 Rủi ro ghi đè baseline — đã phát hiện ở CP0, gửi vai trò 1

`Paths` **không có** field riêng cho quality/freshness của corrupted và repaired: chỉ có `quality_dir` và một `freshness_report` duy nhất (`config.py:99-101`). Nếu gọi y nguyên ở corruption flow thì **freshness baseline bị ghi đè** → vi phạm quy tắc "không ghi đè baseline".

Cách xử lý tôi chọn (không sửa `config.py`, tránh đụng vai trò 1):

- `run_data_quality_checks(df, settings, report_name)` ghi ra `settings.paths.quality_dir / f"{safe_slug(report_name)}_quality.json"` → `baseline_quality.json`, `corrupted_quality.json`, `repaired_quality.json`.
- `build_freshness_report(df, settings, report_path)` nhận `report_path` **tường minh**: baseline dùng `settings.paths.freshness_report`, hai trạng thái kia dùng `quality_dir / "freshness_report_corrupted.json"` và `..._repaired.json`.

---

## 6. Việc CP0 #5 — Định nghĩa signals

### 6.1 Data quality checks (`run_data_quality_checks`)

| Check | Điều kiện pass | Vì sao có mặt |
| --- | --- | --- |
| `row_count_min` | `len(df) >= 10` | phát hiện drop hàng loạt (corruption "drop latest") |
| `paper_id_not_null` | `paper_id` không null/rỗng | ID hỏng làm `retrieval_hit` mất ý nghĩa |
| `paper_id_unique` | `df.paper_id.nunique() == len(df)` | bắt duplicate rows |
| `title_not_null` | `title` không null/rỗng | bắt truncate/blank title |
| `summary_min_chars` | mọi row có `summary_chars >= 100` | bắt blank/truncate summary — ảnh hưởng trực tiếp ground truth `summary` |
| `text_for_embedding_not_empty` | không có giá trị rỗng | rỗng → embedding vô nghĩa → retrieval hỏng |
| `freshness_age_days` | `df.age_days.max() <= settings.freshness_threshold_days` (180, `config.py:64,73`) | bắt corruption "old date" |

Payload JSON (đây cũng là input của `generate_phase1_report`):

```json
{
  "report_name": "baseline",
  "generated_at": "<ISO UTC>",
  "total_rows": 24,
  "success": true,
  "passed": 7,
  "failed": 0,
  "checks": [
    {"name": "paper_id_unique", "success": true, "observed": 24, "expected": "24 unique", "details": ""}
  ],
  "failed_checks": []
}
```

Quy tắc: `success` phải được **tính** từ `all(check["success"])`, không hard-code. Check fail không được raise — flow vẫn chạy tiếp để còn đo được impact lên metric.

### 6.2 Freshness (`build_freshness_report`)

Payload đúng như pseudo-code yêu cầu (`observability/quality.py:24-38`):

```json
{
  "latest_published": "YYYY-MM-DD",
  "oldest_published": "YYYY-MM-DD",
  "stale_rows": 0,
  "total_rows": 24,
  "is_fresh": true
}
```

- `stale_rows` = số row có `age_days > settings.freshness_threshold_days`.
- `is_fresh` = `stale_rows == 0`.
- **Source timestamp**: `age_days` phải do cleaning tính từ `published` so với `run_date` truyền vào (`cleaning.build_clean_dataframe(records, run_date)`), **không** tính lại bằng `datetime.now()` trong observability — nếu tính lại, chạy lần 2 vào ngày khác sẽ ra số khác và baseline không tái lập được.

---

## 7. Việc CP0 #6 — Phác thảo report

### 7.1 `phase1_report.md` (`generate_phase1_report`)

```
# Phase 1 — Baseline Report
1. Source & scope        : source_api, source_query, source_filter, max_results, raw/clean row count
2. Evaluation metrics    : samples, retrieval_hit_rate, mean_token_f1, judge_accuracy, mean_judge_score, ragas status
3. Data quality          : bảng check | pass/fail | observed | expected
4. Freshness             : latest/oldest published, stale_rows/total_rows, is_fresh
5. Evidence & limitations: đường dẫn artifact thật + ghi rõ nếu judge chạy fallback
```

### 7.2 `corruption_report.md` (`generate_corruption_report`) — cột sống của bài

Bảng chính (đúng thứ tự baseline → corrupted → repaired → delta):

| Metric/signal | Baseline | Corrupted | Repaired | Δ (corrupted−baseline) | Δ (repaired−baseline) |
| --- | --- | --- | --- | --- | --- |
| `retrieval_hit_rate` | | | | | |
| `mean_token_f1` | | | | | |
| `judge_accuracy` | | | | | |
| `mean_judge_score` | | | | | |
| quality checks passed | | | | | |
| `is_fresh` / `stale_rows` | | | | | |

Sau bảng là **chuỗi nhân quả**, mỗi mắt xích phải trỏ artifact:

1. `corruption_log.json` (loại corruption, record ID, before/after) → 2. quality/freshness signal đổi (`corrupted_quality.json`) → 3. metric đổi (`corrupted_metrics.json`) → 4. một câu trả lời cụ thể xấu đi (`corrupted_answers.json`, so cùng `id` với `baseline_answers.json`).

Và phần **"Recovery chưa hoàn toàn"**: liệt kê signal/metric nào ở repaired vẫn chưa bằng baseline. Không viết "đã phục hồi hoàn toàn" nếu delta ≠ 0.

---

## 8. Dự đoán trước CP5 (viết bây giờ để CP5 kiểm chứng, không sửa ngược)

| Corruption | Quality check dự kiến fail | Metric dự kiến đổi | Loại câu hỏi bị ảnh hưởng nhất |
| --- | --- | --- | --- |
| Drop latest records | `row_count_min`, freshness `latest_published` lùi | `retrieval_hit_rate` giảm (doc biến mất khỏi index) | mọi loại của paper bị drop |
| Blank summary | `summary_min_chars`, `text_for_embedding_not_empty` | `mean_token_f1` giảm mạnh | `summary` (answer thành chuỗi rỗng) |
| Noise vào summary | `summary_min_chars` có thể vẫn pass | `mean_token_f1` giảm nhẹ, judge score giảm | `summary` |
| Truncate title | không check nào bắt được trực tiếp | `retrieval_hit_rate` giảm vì **exact lookup theo title fail** | mọi loại (mất boost lookup) |
| Old published date | `freshness_age_days`, `is_fresh=false` | `mean_token_f1` giảm ở `date` | `date` |
| Duplicate rows | `paper_id_unique` | hit_rate có thể **không đổi** (vẫn hit), nhưng context bị chiếm chỗ | `summary` |

Điểm cần nói thật trong report: **truncate title là corruption mà quality checks hiện tại không bắt được** — đây chính là ví dụ "signal không đổi nhưng metric xấu đi", và là lý do phải đọc answers chứ không chỉ nhìn quality report.

---

## 9. Checklist CP0 (tự đánh giá)

- [x] Đã đọc `testset.py`, `qa.py`, `metrics.py`; chốt schema 5 field và luật sinh answer.
- [x] Đã thiết kế 4 loại câu hỏi có cụm khóa khớp `_extract_answer`, ground truth lấy từ cột clean.
- [x] Đã chốt `ground_truth_doc_ids = [paper_id]` từ cleaned data, kèm điều kiện kiểm chứng bằng `index.lookup`.
- [x] Đã liệt kê artifact baseline + corruption và phát hiện rủi ro ghi đè freshness/quality.
- [x] Đã định nghĩa 7 quality checks + payload freshness + quy tắc `age_days` tái lập được.
- [x] Đã phác thảo 2 report + chuỗi nhân quả + bảng dự đoán impact.
- [ ] **Chờ**: cleaned dataframe (VT3) để implement `build_test_set` — chưa có `paper_id` ổn định thì không ghi test set.

### Việc của tôi ở các checkpoint sau

- **CP1**: implement 7 quality checks + freshness report; chọn paper đại diện và viết draft question (chưa ghi file test set).
- **CP2**: implement `build_test_set`, ghi `data/eval/test_set.json`, verify mọi doc id tìm được trong index; dựng khung `phase1_report.md`.
- **CP3**: chạy evaluator → `baseline_metrics.json` + `baseline_answers.json`; chạy quality/freshness; sinh `phase1_report.md`; đọc 1 hit + 1 miss.
- **CP5**: evaluate corrupted bằng **test set cũ**; nối corruption log ↔ quality signal ↔ metric change.
- **CP6**: evaluate repaired, tính delta 3 trạng thái, sinh `corruption_report.md`, nêu rõ phần chưa phục hồi.
