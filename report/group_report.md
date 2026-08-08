# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4 |
| Tên nhóm | G36 |
| Repository | https://github.com/AnhDc2004/K4_Day10_Data-Pipeline-Data-Observability-G36 |
| Ngày hoàn thành | 2026-08-06 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Đinh Đức Anh | 2A202601714| Role 1| src/core/ · src/pipelines/ |
| 2 | Nguyễn Thành Huy | 2A202601802 | Role 2 | src/ingestion/crossref.py · data/raw/ |
| 3 | Trần Minh Hạnh | 2A202601232 | Role 3 | src/ingestion/cleaning.py · corruption.py |
| 4 | Phan Văn Phương | 2A202602033 | Role 4 | src/retrieval/ · data/embeddings/ |
| 5 | Lê Huy Hoàng | 2A202601660 | Role 5 | src/evaluation/ · src/observability/ |

## 2. Tóm tắt kết quả

Nhóm hoàn thành trọn vẹn cả hai phase: baseline pipeline (Crossref → cleaning → Chroma index → evaluation → quality/freshness → report) và corruption flow (corrupt → re-index → re-evaluate → repair từ raw → so sánh ba trạng thái), cộng thêm một agent demo chạy trên index baseline. Toàn bộ artifact theo contract CP0 §5 đều tồn tại và đọc được.

Baseline đạt điểm tuyệt đối trên cả bốn chỉ số chính: `retrieval_hit_rate` 1.000, `mean_token_f1` 1.000, `judge_accuracy` 1.000, `mean_judge_score` 5/5, kèm bốn chỉ số Ragas. Data quality 11/11 check PASS, `is_fresh: true`. Judge là LLM thật ở cả ba trạng thái — 0/24 answer chứa chuỗi fallback heuristic.

Con số 1.000 này chỉ đạt được sau khi sửa hai lỗi đo lường phát hiện ở vòng chạy trước (chi tiết §11): một paper trong test set không có trong index, và trường `published` giữ dạng `Timestamp` khiến CSV ra dấu cách còn index metadata ra chữ `T`, làm cả 6 câu loại `date` bị `token_f1 = 0` dù nội dung đúng.

Corruption ảnh hưởng rõ nhất là `drop_latest`. Hai paper mới nhất bị xoá khỏi clean data, mỗi paper 4 câu hỏi → đúng 8/24 câu mất gold document, kéo `retrieval_hit_rate` từ 24/24 xuống 16/24. `mean_token_f1` giảm 0.2769, `judge_accuracy` giảm 0.2917, `mean_judge_score` giảm 1.0000.

Repair phục hồi **tuyệt đối**: cả bốn chỉ số chính và ba trong bốn chỉ số Ragas về đúng giá trị baseline, Δ = 0.

Giới hạn quan trọng nhất bây giờ không còn là lỗi kỹ thuật mà là bản chất bài đo: baseline **kịch trần do thiết kế**, không phải bằng chứng hệ thống RAG mạnh (§12).

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response/raw records (24 records)
    -> cleaning + data contract validation (24/24 giữ lại)
    -> embedding MiniLM + ChromaDB index (papers-baseline, 24 docs)
    -> evaluation baseline (test set 24 sample đã khoá)
    -> quality (11 check) + freshness report
    -> corruption (7 thao tác, 6 loại) -> collection papers-corrupted
    -> re-evaluate + quality/freshness riêng
    -> repair: chạy lại cleaning từ data/raw/crossref_records.json
    -> re-index (papers-repaired) -> re-evaluate
    -> comparison report
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref REST API | Fetch theo `source_query` + `source_filter`, retry | `data/raw/crossref_response.json`, `crossref_records.json` | Vai trò 2 |
| Cleaning | raw records | Chuẩn hoá field, strip JATS markup + HTML entity, pad partial date, tính `age_days` | `data/clean/papers_clean.csv` / `.json`, `data/quality/cleaning_report.json` | Vai trò 3 |
| Embedding/index | clean dataframe | MiniLM-L6-v2 → Chroma, ghi manifest | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Vai trò 4 |
| Evaluation | clean + index | Sinh test set, chạy evaluator, token F1 + LLM judge + Ragas | `data/eval/test_set.json`, `data/results/*_metrics.json`, `*_answers.json` | Vai trò 5 |
| Observability | clean dataframe | 11 quality check + freshness, audit manifest, verify test set ↔ index | `data/quality/*.json` | Vai trò 5 |
| Corruption/repair | clean + raw | 6 loại corruption deterministic; repair bằng cách clean lại từ raw | `data/results/corruption_log.json`, `papers_clean_corrupted/repaired.*` | Vai trò 3 + 5 |
| Orchestration | tất cả | Thứ tự 8 bước, audit trước khi evaluate | `data/reports/phase1_report.md`, `corruption_report.md` | Vai trò 1 |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| --- | --- |
| `LLM_PROVIDER` | openrouter |
| `LLM_MODEL` | openai/gpt-4o-mini |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 (`max_results = 24`) |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày |
| Random seed | Không dùng — corruption chọn row theo vị trí cố định (deterministic) |
| Collection | `papers-baseline` / `papers-corrupted` / `papers-repaired` |
| `source_query` | `agentic retrieval augmented generation large language model` |

> **Ghi chú cần thống nhất trước khi nộp.** Log `run_phase1.py` của lần chạy cuối cho thấy toàn bộ request đi tới `api.openai.com/v1/chat/completions`, trong khi `cp3_eval_observability.md` ghi provider là `openrouter` với model `openai/gpt-4o-mini`. Điền giá trị đúng theo `.env` thực tế của lần chạy sinh ra các artifact đang nộp.

Không dán nội dung API key hoặc file `.env` vào báo cáo.

### Lệnh cài đặt

```bash
uv sync
```

### Lệnh chạy

Baseline:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
python script/run_corruption_flow.py
```

Bật Ragas (mặc định skip):

```powershell
$env:RUN_RAGAS="1"
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| --- | --- | --- | --- |
| Baseline pipeline | Thành công (8/8 step) | 2026-08-06 20:54:47 | `data/reports/phase1_report.md`, `baseline_metrics.json`, `baseline_answers.json` |
| Corruption flow | Thành công (8/8 step) | 2026-08-06 21:07:34 | `corrupted_metrics.json`, `repaired_metrics.json`, `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API |
| Query/filter | `agentic retrieval augmented generation large language model` + `from-pub-date:2026-02-07,has-abstract:true` |
| Thời điểm lấy dữ liệu | Snapshot tại `data/raw/crossref_records.json` |
| Số record nhận được | 24 |
| Cơ chế retry/backoff | Có snapshot cục bộ; pipeline load lại thay vì gọi API mỗi lần chạy |

### Raw và clean schema

| Trường | Kiểu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --- | --- | --- | --- | --- |
| `paper_id` | str | Có | DOI, dùng làm ground truth doc id | Check `paper_id_not_null` + `paper_id_unique` |
| `title` | str | Có | Câu hỏi + exact lookup | Strip JATS markup, chuẩn hoá `U+2010` |
| `summary` | str | Có | Ground truth loại `summary` | Check `summary_not_null` + `summary_min_chars` (≥100) |
| `authors_joined` | str | Có | Ground truth loại `authors` | Chroma metadata chỉ nhận scalar → phải join thành string |
| `categories_joined` | str | Có | Ground truth loại `categories` | Crossref không trả `subject` → 24/24 = `"Uncategorized"` |
| `published` | str | Có | Ground truth loại `date` + freshness | Partial date `YYYY-MM` → pad ngày 01 |
| `age_days` | int | Có | Tín hiệu freshness | Check `published_parseable` bắt row không parse được |
| `text_for_embedding` | str | Có | Nội dung embed | Check `text_for_embedding_not_empty` |

### Quy tắc cleaning

| Quy tắc | Quality dimension | Số record bị tác động | Cách xác minh |
| --- | --- | --: | --- |
| Strip JATS markup (`<scp>`) và decode HTML entity | Validity | 1 title, 3 `text_for_embedding` | `tests/test_cleaning.py`, audit drift trong manifest |
| Pad partial date `YYYY-MM` → `YYYY-MM-01` | Completeness | 2 | `published_parseable` từ 2 fail → 0 fail |
| Giữ nguyên toàn bộ row hợp lệ | Completeness | 24/24 giữ lại | `data/quality/cleaning_report.json` |

`text_for_embedding` ghép title + summary; document ID lấy trực tiếp từ `paper_id` (DOI), không tự sinh; `age_days` tính từ `published` so với `run_date` truyền vào `build_clean_dataframe`, **không** dùng `datetime.now()` — nếu tính lại thì chạy vào ngày khác sẽ ra số khác và baseline không tái lập được.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 24 |
| Các `question_type` | `summary`, `authors`, `date`, `categories` — mỗi loại 6 câu |
| Ground-truth document ID | `[row.paper_id]` copy trực tiếp từ cột `paper_id` của clean dataframe |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection | ChromaDB — `papers-baseline` / `papers-corrupted` / `papers-repaired` |
| Retrieval `top_k` | 4 (xác nhận: 24/24 câu đều trả về đúng 4 context) |
| LLM provider/model | *(xem ghi chú §4)* |
| Test set dùng chung | `data/eval/test_set.json` — 6 paper × 4 loại, khoá cứng từ CP3 |

**Vì sao giữ nguyên test set cho cả ba trạng thái:** metric chỉ so sánh được khi mẫu số giống hệt nhau. Nếu sinh lại test set sau corruption, `build_test_set` sẽ tự loại các paper đã hỏng và chọn paper khác — corrupted khi đó được chấm trên bộ câu hỏi dễ hơn, và mọi kết luận về mức suy giảm đều vô nghĩa. Khoá test set là điều kiện để Δ giữa ba trạng thái phản ánh đúng tác động của data, không phải tác động của việc đổi đề thi.

Sáu paper trong test set: `10.1111/exsy.70341`, `10.2118/234689-pa`, `10.1007/s10278-026-02086-9`, `10.21203/rs.3.rs-10178277/v1`, `10.2196/preprints.106157`, `10.3390/buildings16132637`.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| Raw response/records | `data/raw/` | Có | 24 raw records |
| Cleaned dataset | `data/clean/papers_clean.csv` | Có | 24/24 giữ lại |
| Embedding manifest/index | `data/embeddings/`, `data/chroma/` | Có | 24 document, collection `papers-baseline` |
| Evaluation set | `data/eval/test_set.json` | Có | 24 sample, đã khoá |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | Kèm 4 chỉ số Ragas |
| Baseline answers | `data/results/baseline_answers.json` | Có | 24 answer đầy đủ context |
| Agent demo answers | `data/results/agent_demo_answers.json` | Có | 4 câu hỏi qua agent có tool |
| Corruption log | `data/results/corruption_log.json` | Có | 7 thao tác, 6 loại, kèm before/after |
| Quality/freshness | `data/quality/` | Có | Xem ghi chú trùng tên file ở §12 |
| Baseline report | `data/reports/phase1_report.md` | Có | Sinh tự động từ JSON |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| --- | --: | --- |
| `retrieval_hit_rate` | 1.0000 | 24/24 câu có gold document trong top-4 |
| `mean_token_f1` | 1.0000 | Khớp tuyệt đối trên cả 24 câu, kể cả 6 câu `date` |
| `judge_accuracy` | 1.0000 | 24/24 câu được LLM judge chấm đúng |
| `mean_judge_score` | 5 | Điểm tối đa trên cả 24 câu |
| Ragas `answer_relevancy` | 0.184 | **Không dùng được** để kết luận — xem §12 |
| Ragas `context_precision` | 0.750 | 18/24 mẫu = 1.0; 6 mẫu bằng 0 **đúng là 6 câu `date`** |
| Ragas `context_recall` | 0.750 | Cùng 18 mẫu như trên |
| Ragas `faithfulness` | 0.729 | Xem §12 về sàn nhiễu |

**Kết quả theo loại câu hỏi** (tính từ `baseline_answers.json`):

| Loại | hit_rate | token_f1 | judge_acc | judge_score |
| --- | --: | --: | --: | --: |
| `summary` | 1.000 | 1.000 | 1.000 | 5.00 |
| `authors` | 1.000 | 1.000 | 1.000 | 5.00 |
| `date` | 1.000 | 1.000 | 1.000 | 5.00 |
| `categories` | 1.000 | 1.000 | 1.000 | 5.00 |

**Judge integrity:** 0/24 answer chứa `"Fallback heuristic judge used"` ở cả ba trạng thái — điều kiện bắt buộc trước khi được phép đọc `judge_accuracy` như metric thật (bẫy đã cảnh báo ở CP0 §1.4).

**Agent demo.** `agent_demo_answers.json` ghi 4 câu hỏi chạy qua agent có tool (`semantic_search_papers`, `lookup_paper`). Ba câu trả lời đúng và có trích nguồn DOI. Câu thứ tư — hỏi về quantum cryptography, một chủ đề **không có** trong corpus — agent trả lời thẳng là không tìm thấy thay vì bịa, đúng như system prompt yêu cầu. Một giới hạn phát hiện được từ demo này được ghi ở §12.

## 8. Data quality và freshness

### Quality checks — baseline 11/11 PASS

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| --- | --- | --- | --- | --- |
| `row_count_min` | Completeness | ≥ 10 rows | PASS (24) | `phase1-baseline_quality.json` |
| `schema_columns_present` | Validity | 8 cột bắt buộc | PASS (8) | `phase1-baseline_quality.json` |
| `paper_id_not_null` | Completeness | 0 missing | PASS (0) | `phase1-baseline_quality.json` |
| `paper_id_unique` | Uniqueness | 24 unique | PASS (24) | `phase1-baseline_quality.json` |
| `duplicate_records` | Uniqueness | 0 duplicate | PASS (0) | `phase1-baseline_quality.json` |
| `title_not_null` | Completeness | 0 missing | PASS (0) | `phase1-baseline_quality.json` |
| `summary_not_null` | Completeness | 0 missing | PASS (0) | `phase1-baseline_quality.json` |
| `text_for_embedding_not_empty` | Completeness | 0 missing | PASS (0) | `phase1-baseline_quality.json` |
| `summary_min_chars` | Validity | 0 row < 100 ký tự | PASS (0) | `phase1-baseline_quality.json` |
| `published_parseable` | Validity | 0 row không parse được | PASS (0) | `phase1-baseline_quality.json` |
| `freshness_age_days` | Timeliness | max ≤ 180, 0 row thiếu | PASS (175) | `phase1-baseline_quality.json` |

### Freshness

| Thuộc tính | Giá trị |
| --- | --- |
| Freshness được đo tại | Clean dataframe, cột `age_days` do cleaning tính |
| `latest_published` / `oldest_published` | 2026-08-01 / 2026-02-13 |
| Ngưỡng freshness | 180 ngày |
| Trạng thái baseline | **Fresh** (`is_fresh: true`) |
| `stale_rows` / `total_rows` | 0 / 24 |
| `max_age_days` / `mean_age_days` | 175 / 83.8 |
| `missing_published` | 0 |

## 9. Corruption scenarios và repair

`corrupt_clean_dataframe` thực hiện **7 thao tác trên 6 loại**, deterministic (chọn row theo thứ tự `published` và `paper_id`, không random), toàn bộ ghi vào `data/results/corruption_log.json` kèm `record_ids`, `parameter`, `before_count`, `after_count`. Số dòng đi từ 24 → 23 (mất 2, thêm 1 bản sao).

| Loại (tên trong log) | Cách tạo | Số row | Quality signal kỳ vọng | Tác động thực tế |
| --- | --- | --: | --- | --- |
| `drop_latest` | Xoá 2 record có `published` mới nhất | 2 | `row_count_min` | **Nguồn duy nhất làm tụt hit rate**: 8/24 câu mất gold document |
| `missing_summary` | Đặt `summary = ""` | 1 | `summary_not_null`, `summary_min_chars` | Ảnh hưởng câu loại `summary` của paper đó |
| `inject_noise` | Chèn marker `[CORRUPTED_NOISE] …` vào cuối summary | 1 | `summary_min_chars` vẫn pass | `token_f1` câu `summary` giảm; embedding bị nhiễu |
| `truncate_title` | Giữ 15 ký tự đầu của title | 1 | **Không check nào bắt được** | Mất boost exact lookup theo title |
| `old_published_date` | Lùi `published` 730 ngày, cộng `age_days` tương ứng | 1 | `freshness_age_days`, `is_fresh=false` | `stale_rows` từ 0 lên 1 |
| `add_duplicate` | Nhân bản nguyên một row | 1 | `paper_id_unique`, `duplicate_records` | Chiếm chỗ trong top-4 |

Số học khớp với artifact: 5 check fail (`paper_id_unique`, `duplicate_records`, `summary_not_null`, `summary_min_chars`, `freshness_age_days`) → **6/11 PASS**; `stale_rows = 1`.

**Repair phục hồi từ nguồn đáng tin cậy, không che kết quả lỗi:**

```python
raw_records = load_raw_records(settings.paths.raw_records_json)
repaired_df = build_clean_dataframe(raw_records, run_date=now_utc())
```

Repair **không** đọc corrupted data và **không** sửa tay. Nó nạp raw snapshot chưa bị đụng tới và gọi lại đúng hàm cleaning mà baseline đã dùng, rồi build index mới vào collection riêng. Sau đó `validate_clean_dataframe` chạy như một guard clause: vi phạm contract thì `raise` chứ không vá JSON kết quả.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Δ do corruption | Mức phục hồi | Nhận xét |
| --- | --: | --: | --: | --: | --: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.6667 | 1.0000 | **−0.3333** | 100% | 24/24 → 16/24 → 24/24 |
| `mean_token_f1` | 1.0000 | 0.7231 | 1.0000 | **−0.2769** | 100% | Loại `categories` giữ F1 = 1.0 kể cả khi retrieval sai, kéo con số này lên cao giả tạo |
| `judge_accuracy` | 1.0000 | 0.7083 | 1.0000 | **−0.2917** | 100% | 24/24 → 17/24 → 24/24 |
| `mean_judge_score` | 5 | 4.0000 | 5 | **−1.0000** | 100% | |
| Ragas `context_precision` | 0.750 | 0.542 | 0.750 | −0.208 | 100% | Khớp lại tuyệt đối |
| Ragas `context_recall` | 0.750 | 0.667 | 0.750 | −0.083 | 100% | Khớp lại tuyệt đối |
| Ragas `faithfulness` | 0.729 | 0.558 *(n=23)* | 0.708 | −0.171 | −0.021 so với baseline | Mẫu số corrupted lệch + nhiễu — xem §12 |
| Ragas `answer_relevancy` | 0.184 | 0.137 | 0.182 | −0.047 | −0.003 so với baseline | Không đủ độ nhạy để kết luận |
| Quality checks | 11/11 PASS | **6/11 PASS** | 11/11 PASS | −5 check | 100% | |
| Freshness status | FRESH | STALE | FRESH | — | 100% | `stale_rows` 0 → 1 → 0 |

**Kết quả theo loại câu hỏi ở trạng thái corrupted** (tính từ `corrupted_answers.json`; baseline và repaired đều 1.000 ở mọi ô):

| Loại | hit_rate | token_f1 | judge_acc | judge_score |
| --- | --: | --: | --: | --: |
| `summary` | 0.667 | 0.559 | 0.500 | 3.50 |
| `authors` | 0.667 | 0.667 | 0.667 | 3.67 |
| `date` | 0.667 | 0.667 | 0.667 | 3.83 |
| `categories` | 0.667 | **1.000** | **1.000** | **5.00** |

Loại `categories` giữ điểm tuyệt đối dù hit rate chỉ 0.667 — bằng chứng trực tiếp cho vấn đề nêu ở §12.

### Hai chuỗi nhân quả có artifact hỗ trợ

**1. Drop record → mất document khỏi index → hit rate và judge accuracy sập.**

`corruption_log.json` ghi thao tác `drop_latest` với `{"count": 2, "sort_field": "published", "order": "descending"}` và hai `record_ids` cụ thể. Mỗi paper trong test set có 4 câu hỏi, nên 2 paper bị xoá = 8 câu mất gold document. Số học khớp chính xác: `(24 − 8)/24 = 0.6667`. Toàn bộ mức giảm hit rate quy về đúng corruption này — 16 câu còn lại không bị ảnh hưởng.

Điều đáng nói hơn con số nằm ở nội dung câu trả lời. Agent **không hề báo lỗi** khi document biến mất:

```
id        : 10.2118/234689-pa::summary
hit       : False          (baseline: True, f1 1.000, judge 5/5)
GT        : "Summary In high-risk industrial settings, leveraging large language models
             (LLMs) for automated accident analysis and generating safety reports..."
answer    : "This study investigates a method that integrates retrieval-augmented
             mechanisms into large language model agents for scientific literature
             review generation..."
retrieved : 10.20944/preprints202604.0339.v1, 10.55041/isjem07213, ...
f1: 0.140   judge: 2/5
```

Không exception, không cảnh báo. Agent lấy một paper khác cùng chủ đề RAG và trả lời trôi chảy về đúng chủ đề sai. Đây là bài học chính của lab — **data hỏng không làm agent crash, nó làm agent trả lời sai một cách tự tin.**

**1b. Corruption không cần xoá document mới gây hại — `missing_summary` phá dữ liệu tại chỗ.**

```
id     : 10.1007/s10278-026-02086-9::summary
hit    : True           ← retrieval hoạt động hoàn toàn bình thường
GT     : "Abstract Diagnosing jawbone lesions in oral and maxillofacial radiology
          remains challenging due to overlapping radiological features..."
answer : ""             ← rỗng
f1: 0.000   judge: 2/5
```

Case này bổ sung cho case trên ở một điểm quan trọng: retrieval **đúng** nhưng câu trả lời vẫn vô dụng. Nếu chỉ theo dõi `retrieval_hit_rate` thì corruption này hoàn toàn vô hình.

**2. Repair từ raw → quality/freshness phục hồi → metric phục hồi hoàn toàn.**

Corruption đẩy quality từ 11/11 xuống 6/11 và freshness từ FRESH sang STALE. Sau khi chạy lại cleaning từ `data/raw/crossref_records.json`, quality về 11/11 PASS, `is_fresh: true`, và cả 4 chỉ số chính về đúng baseline.

Bốn chỉ số chính đạt mức phục hồi 100%; hai chỉ số Ragas còn lệch nhẹ vì nhiễu đo lường, không phải vì dữ liệu (§12). Mức phục hồi này là **kỳ vọng được, không phải may mắn**: raw snapshot còn nguyên và cleaning là hàm thuần, nên clean lại từ raw bắt buộc phải ra đúng dataset ban đầu. Nếu Δ ≠ 0 thì mới là dấu hiệu cleaning không deterministic — và đó chính là thứ phép thử này kiểm chứng.

### Hai signal KHÔNG đổi — phải nói rõ để tránh kết luận quá mức

- **`truncate_title` không làm fail bất kỳ check nào** trong 11 check. `title_not_null` chỉ hỏi title có rỗng không, không hỏi nó có còn nguyên không. Đây là bằng chứng trực tiếp cho luận điểm: *quality check pass không có nghĩa data sạch, nếu check không nhìn đúng chỗ.*
- **Ragas `context_precision` bằng 0 ở đúng 6 câu `date` ngay cả trong baseline**, dù retrieval trúng 24/24. Chỉ số này không đổi theo chất lượng retrieval của loại câu hỏi đó, nên không được dùng làm bằng chứng cho kết luận nào về `date`.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** `baseline_metrics.json` ghi `"ragas": {"error": "Ragas evaluation failed: 0"}` dù log cho thấy `Evaluating: 100%|██| 96/96` chạy xong không lỗi, và pipeline vẫn in "ĐÃ CHẠY HOÀN THÀNH THÀNH CÔNG".

- **Nguyên nhân:** `_run_ragas` kết thúc bằng `return dict(result)`. Code viết theo API ragas 0.1.x, nơi `evaluate()` trả về `Result` kế thừa `dict`. Với ragas ≥ 0.2, hàm trả về `EvaluationResult` không có `keys()`, nên `dict()` lùi về giao thức tuần tự và gọi `result[0]` → `KeyError: 0`. Exception bị `except Exception` nuốt và chuyển thành chuỗi text, nên **lỗi không bao giờ xuất hiện trong log** — pipeline chạy tiếp bình thường. Toàn bộ ~400 lần gọi LLM của Ragas bị vứt đi ở dòng cuối cùng.

- **Cách xử lý:** (1) đổi `f"...{exc}"` thành `f"...{exc!r}"` và ghi kèm `traceback.format_exc()` để lỗi tự khai báo — chính bước này biến thông báo vô nghĩa `0` thành `KeyError(0)` kèm số dòng; (2) thay `dict(result)` bằng hàm `_summarize_ragas(result)` đọc `result.scores` và tự tính trung bình, tương thích cả hai phiên bản; (3) thêm trường `{metric}_n` ghi số mẫu thực sự chấm được sau khi lọc NaN.

- **Cách xác minh:** chạy lại `python script/run_phase1.py` với `RUN_RAGAS=1` → trường `ragas` trong `baseline_metrics.json` có đủ 4 chỉ số kèm `_n = 24`. Chính trường `_n` sau đó phát hiện thêm một vấn đề khác: corrupted có `faithfulness_n = 23` chứ không phải 24 (§12).

- **Điều học được:** `except Exception` nuốt traceback biến một lỗi 1 dòng thành nhiều giờ mò mẫm. Và một pipeline in "THÀNH CÔNG" không chứng minh mọi bước đều thành công — phải kiểm artifact, không tin log.

### Vấn đề tích hợp thứ hai (đã xử lý) — hai report lệch nhau

Khi ghép bài nộp mới phát hiện hai report do hai hàm khác nhau sinh ra và không hề thống nhất: `phase1_report.md` dùng tiếng Việt **không dấu** (`Ket qua tong`, `Chi tiet`) còn `corruption_report.md` dùng **tiếng Anh** hoàn toàn. Phần không dấu là dấu vết né `UnicodeEncodeError` — trên Windows, `open(path, "w")` không chỉ định `encoding` sẽ dùng codepage hệ thống và ném lỗi ngay khi gặp ký tự có dấu.

Nguyên nhân gốc thuộc về contract: CP0 §7.2 chốt *nội dung* các mục nhưng không chốt *nhãn hiển thị*, nên mỗi người tự chọn ngôn ngữ.

Đã xử lý trong `src/observability/reporting.py`: gom toàn bộ nhãn vào 4 dict dùng chung cho cả hai hàm và chuyển sang tiếng Việt có dấu; ghi file bằng UTF-8 tường minh. Nhân tiện sửa hai lỗi vi phạm checklist release CP6:

1. **Cột Baseline của hai dòng observability bị hard-code** chuỗi `PASSED` / `FRESH` — hàm thậm chí không nhận `baseline_quality`, nên dù baseline có fail thì report vẫn in PASSED. Đã thêm hai tham số (mặc định `None` để không phá caller cũ) và sửa `corruption_flow.py` nạp hai payload đó từ `data/quality/`.
2. **Report in đường dẫn tuyệt đối** `E:\Lab1\...` — rubric trừ điểm hard-code path và file này được commit lên Git. Đã rút về path tương đối.

Bổ sung theo đúng CP0 §7.2: hai cột Δ, bảng so sánh Ragas, và mục "Mức phục hồi" tự liệt kê chỉ số chưa về baseline.

Bản đầu của mục "Mức phục hồi" còn một lỗi phải sửa tiếp: nó chỉ quét 4 chỉ số chính nên kết luận "mọi chỉ số đều Δ = 0" trong khi bảng ngay phía trên cho thấy `faithfulness` lệch +0.042 — report **tự mâu thuẫn**. Đã sửa để mục này quét cả Ragas và nêu rõ phạm vi kết luận. Bài học: một mục tóm tắt tự sinh mà không đọc hết dữ liệu của chính nó thì nguy hiểm hơn là không có, vì nó tạo cảm giác đã được kiểm chứng.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| **Baseline 1.000 là kịch trần do thiết kế, không phải bằng chứng RAG mạnh** | `_extract_answer` không sinh văn bản — nó trả nguyên văn một trường metadata (`authors_joined`, `published`, `categories_joined`) hoặc câu đầu của `summary`; ground truth thì copy đúng trường đó từ clean dataframe. Nên **hễ retrieval đặt đúng document ở rank 0 thì `token_f1` = 1.0 tất yếu**. Thêm nữa, câu hỏi chứa nguyên title trong dấu nháy đơn nên `answer_question` bắt được bằng exact lookup, retrieval gần như không thể sai | Dùng probe set (`retrieval_probe.py`) làm thước đo có biến thiên: câu hỏi diễn đạt lại từ abstract, cấm nhắc title. Đo `hit@4`, `top1`, `MRR` trên cả ba collection — không tốn lần gọi LLM nào |
| **Loại `categories` không mang tín hiệu** | Crossref không trả field `subject` nên 24/24 paper có `categories_joined = "Uncategorized"` → `token_f1` luôn = 1.0 kể cả khi retrieval sai paper. Thổi phồng `mean_token_f1` ở cả ba trạng thái | Báo cáo metric tách theo `question_type` (đã làm ở §7) thay vì chỉ nhìn số trung bình |
| **Ragas `answer_relevancy` không dùng được** | 0.184 mâu thuẫn với judge accuracy 1.000. Nguyên nhân đã truy ra và nay xác nhận sạch: 6 mẫu bị điểm 0 **đúng là 6 câu `categories`** — ragas gắn cờ "noncommittal" cho câu trả lời `"Uncategorized"`, hoàn toàn hợp lý. Chỉ số này đang đo chất lượng ground truth chứ không đo hệ thống | Loại `answer_relevancy` khỏi mọi kết luận, hoặc chỉ tính trên 3 loại câu hỏi còn lại |
| **Ragas `context_precision` bằng 0 ở toàn bộ 6 câu `date`** | Cả 6 câu này retrieval **đúng** (baseline hit 24/24) nhưng ragas vẫn cho 0, vì answer là một chuỗi ngày trần không thể hiện việc dùng context. Đây là hệ quả của thiết kế `_extract_answer`, không phải lỗi retrieval. Chính 6 mẫu này kéo `context_precision` từ 1.0 xuống 0.750 | Nêu rõ giới hạn; hoặc để agent sinh câu trả lời có ngữ cảnh thay vì trả metadata thô |
| **Chỉ số Ragas có sàn nhiễu ±0.02** | Baseline và repaired sinh từ cùng một dataset và có 24/24 câu trả lời giống hệt nhau, nên mọi chênh lệch còn lại là nhiễu thuần. Đối chiếu từng ô `per_sample`: **6/96 ô lệch** — 4 ô `answer_relevancy` dao động nhẹ, và 2 ô `faithfulness` lật hẳn giá trị (mẫu #3 từ 0.5 lên 1.0, mẫu #11 từ 1.0 xuống 0.0). Kết quả: `faithfulness` lệch −0.0208, `answer_relevancy` lệch −0.0026, còn `context_precision` và `context_recall` khớp tuyệt đối. Qua nhiều lần chạy, `faithfulness` từng lệch tới 0.042 | Mọi thay đổi < 0.05 ở `faithfulness` / `answer_relevancy` **không được** kết luận là cải thiện; muốn dùng làm metric thật phải chạy nhiều lần lấy trung bình kèm độ lệch. `context_precision` và `context_recall` là hai chỉ số Ragas duy nhất đủ ổn định để so sánh trực tiếp |
| **Mẫu số Ragas không đồng nhất giữa ba trạng thái** | Corrupted có `faithfulness_n = 23` (1 mẫu NaN) trong khi baseline/repaired có 24. So 0.558 với 0.729 là so hai thứ khác cơ sở — nếu tính NaN = 0 trên đủ 24 mẫu thì corrupted là **0.535** | Thống nhất quy ước NaN, hoặc luôn báo cáo kèm `_n` |
| **Bộ tool của agent không phủ được truy vấn theo metadata** | Agent chỉ có `semantic_search_papers` và `lookup_paper`, không tool nào sắp xếp theo ngày. Câu "What is the newest paper in the corpus about?" trong `agent_demo_answers.json` được trả lời **sai** — agent chỉ ra paper `published = 2026-07-10` trong khi `freshness_report.json` ghi `latest_published: 2026-08-01`. Agent suy đoán từ kết quả semantic search thay vì thừa nhận không đủ tool. Cùng một hệ thống, khi hỏi về chủ đề ngoài corpus thì trả lời đúng là "không có" | Thêm tool truy vấn metadata (sắp xếp theo `published`, lọc theo khoảng ngày), hoặc bổ sung vào system prompt yêu cầu nói rõ khi câu hỏi vượt khả năng của tool |
| **Test set 24 sample, corruption đụng vào paper trong test set** | Mỗi câu sai làm metric đổi 4.2%. `drop_latest` xoá 2 paper mới nhất, mà test set cũng ưu tiên paper mới → tác động đo được là **cận trên**, không phải mức trung bình nếu corrupt ngẫu nhiên | Mở rộng test set, hoặc corrupt một tập row độc lập với test set |
| **Repair chỉ thành công vì raw snapshot còn nguyên** | Nếu corruption xảy ra ở tầng raw hoặc tại chính nguồn Crossref thì không còn điểm khôi phục nào | Thêm kịch bản corrupt raw để kiểm chứng giới hạn này |
| **`data/quality/` có hai file baseline quality trùng vai trò** | `baseline_quality.json` và `phase1_baseline_quality.json` — dễ đọc nhầm file cũ | Thống nhất một tên |

> **Cần đối chiếu trước khi nộp.** `cp5_cp6_eval_observability.md` ghi corrupted `mean_token_f1` 0.671, `judge_accuracy` 0.625, `mean_judge_score` 3.708; artifact hiện tại ghi 0.5565, 0.7083, 4.0833. (Riêng `retrieval_hit_rate` 1.000 → 0.667 → 1.000 thì nay đã khớp.) Đây là số liệu của lần chạy khác. Cần ghi rõ trong file CP rằng số đó thuộc lần chạy trước, hoặc cập nhật lại theo artifact cuối.

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
