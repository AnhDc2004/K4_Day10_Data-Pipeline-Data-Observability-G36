# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Lê Huy Hoàng |
| MSSV | 2A202601660 |
| Khóa/Lớp | K4 |
| Tên nhóm | G36 |
| Vai trò chính | Thành viên 5 — Evaluation & Observability |
| Repository | https://github.com/AnhDc2004/K4_Day10_Data-Pipeline-Data-Observability-G36 |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Evaluation set | `src/evaluation/testset.py`: `build_test_set`, `select_representative_papers`, `draft_questions`, `validate_test_set`, `verify_test_set_against_index` | cleaned dataframe (vai trò 2), index (vai trò 4) | `data/eval/test_set.json` (24 sample) | Hoàn thành |
| Data quality checks | `src/observability/quality.py`: `run_data_quality_checks` | cleaned dataframe của từng trạng thái | `data/quality/{baseline,corrupted,repaired}_quality.json` | Hoàn thành |
| Freshness monitoring | `src/observability/quality.py`: `build_freshness_report` | `published`, `age_days` | `data/quality/freshness_report*.json` | Hoàn thành |
| Index audit | `src/observability/quality.py`: `audit_index_manifest` | embedding manifest + cleaned dataframe | kết quả audit dùng trong flow | Hoàn thành |
| Reporting | `src/observability/reporting.py`: `generate_phase1_report`, `generate_corruption_report` | metrics/quality/freshness JSON | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Hoàn thành |
| Probe set đo retrieval (bổ sung) | `src/evaluation/retrieval_probe.py`: `build_probe_set`, `evaluate_retrieval` | cleaned dataframe, index | `data/eval/test_set_retrieval_probe.json`, `data/results/retrieval_probe_*.json` | Hoàn thành |
| Corruption & flow (mở rộng, có thống nhất với nhóm) | `src/ingestion/corruption.py`: `corrupt_clean_dataframe`; `src/pipelines/corruption_flow.py` | baseline clean data, raw records | corruption log, corrupted/repaired artifacts, comparison report | Hoàn thành |

Hai file cuối vốn thuộc vai trò 3 và vai trò 1. Đến CP5 hai file này vẫn `NotImplementedError` nên phần CP5/CP6 của tôi không có dữ liệu để đánh giá; nhóm thống nhất để tôi implement để pipeline chạy được end-to-end. Tôi ghi rõ ở đây để không nhận nhầm ownership.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Phát hiện ingestion không dùng `Settings` | Vai trò 1 (`crossref.py`) | Raw response ghi `search-terms: "machine learning"`, 5 record, không có `from-pub-date`/`has-abstract` — trong khi config yêu cầu query agentic RAG, `rows=24`. Sau khi sửa: 24 record, summary đủ 24/24 |
| Phát hiện partial date bị mất im lặng | Vai trò 1 + 2 | 2 record có `published = "2026-08"`/`"2026-07"` → `NaN`; đã được cleaning pad thành ngày 01 |
| Phát hiện index không load được trên máy khác | Vai trò 4 (`index.py`) | Manifest ghi `persist_path` = `W:\AI\...` → `LocalEmbeddingIndex.load()` báo `InternalError: failed to create whole tree`; đã sửa |
| Phát hiện index lệch nội dung so với clean | Vai trò 4 | Sau khi cleaning strip JATS markup, index cũ còn `<scp>RAG</scp>` → 1 title + 3 `text_for_embedding` lệch; đã rebuild |
| Resolve merge conflict đang treo | Cả nhóm | `data/quality/freshness_report.json` còn `<<<<<<< HEAD` làm JSON hỏng và corruption flow crash |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Xây test set 4 loại câu hỏi từ cleaned data | `testset.py::build_test_set` | 24 sample = 6 paper × 4 loại | `verify_test_set_against_index` → `missing_doc_ids: []`, `missing_titles: []` |
| 11 data quality checks | `quality.py::run_data_quality_checks` | baseline 11/11 PASS, corrupted 6/11 | `data/quality/*_quality.json` |
| Freshness monitoring | `quality.py::build_freshness_report` | baseline `is_fresh: true`, corrupted `false` | `data/quality/freshness_report*.json` |
| Baseline evaluation | `metrics.evaluate_pipeline` | `retrieval_hit_rate 1.000`, `mean_token_f1 1.000` | `data/results/baseline_metrics.json` |
| Corruption flow end-to-end | `corruption_flow.py` | 16 corruption, 3 trạng thái đủ artifact | `uv run python script/run_corruption_flow.py` |
| Comparison report | `reporting.py::generate_corruption_report` | bảng 3 trạng thái + delta | `data/reports/corruption_report.md` |

Một output cụ thể phần việc của tôi tạo ra và giúp xác minh:

`data/reports/corruption_report.md` — mọi con số trong đó đọc trực tiếp từ artifact JSON, không nhập tay. Report tự phát hiện hai điều mà người viết dễ bỏ sót: metric nào **chưa** phục hồi về baseline, và trạng thái nào có LLM judge bị rơi về heuristic.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline cần một thước đo đáng tin để trả lời: dữ liệu xấu có thực sự làm RAG agent kém đi không, kém ở đâu, và repair có phục hồi được không. Nếu test set hoặc quality checks sai, mọi kết luận sau đó đều vô nghĩa — metric sẽ tụt vì lỗi đo chứ không phải vì data.

### Cách triển khai

**Test set.** `_extract_answer` trong `qa.py` không sinh văn bản mà trả nguyên văn một trường metadata (`authors_joined`, `published`, `categories_joined`) hoặc câu đầu `summary`, và route bằng cách khớp chuỗi trên câu hỏi (`who authored`, `when was`, `what categories`). Vì vậy câu hỏi phải chứa đúng cụm khóa tiếng Anh, còn `ground_truth` phải **copy nguyên văn trường nguồn** của chính row đó. `ground_truth_doc_ids` lấy trực tiếp từ cột `paper_id`, không tự sinh ID.

**Quality checks.** 11 check: row count, schema đủ cột, `paper_id` not-null/unique, duplicate records, title/summary missing, summary tối thiểu 100 ký tự, `text_for_embedding` không rỗng, `published` parse được, `age_days` trong ngưỡng 180 ngày. Check fail **không raise** — pipeline chạy tiếp để còn đo được tác động lên metric. Cột thiếu thì check fail kèm `details` thay vì `KeyError`.

**Freshness.** Chỉ đọc `age_days` do cleaning tính từ `run_date` truyền vào, **không** tính lại bằng `datetime.now()` — tính lại thì chạy vào ngày khác sẽ ra số khác và baseline không tái lập được.

**Corruption.** 6 loại (drop latest, blank summary, noise, truncate title, stale date, duplicate row), chọn row theo vị trí ổn định chứ không random, để chạy lại ra đúng một corrupted dataset.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | cleaned dataframe với `paper_id, title, summary, authors_joined, categories_joined, published, age_days, text_for_embedding`; `LocalEmbeddingIndex` build từ đúng dataframe đó |
| Output | `test_set.json` (5 key: `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`); quality/freshness JSON; hai report Markdown |
| Module phụ thuộc | `ingestion/cleaning.py`, `retrieval/index.py`, `retrieval/qa.py`, `evaluation/metrics.py` |
| Module sử dụng output | `pipelines/phase1.py`, `pipelines/corruption_flow.py` |
| Điều kiện lỗi cần xử lý | cột thiếu; `published` không parse được; `age_days` là `NaN`; paper_id trong test set không có trong index; LLM judge rơi về heuristic; manifest trỏ path máy khác |

### Cách xác minh

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
python -m unittest discover -s tests
```

- **Kết quả mong đợi:** baseline metrics kịch trần, corrupted tụt rõ trên các metric không cần LLM, repaired về đúng baseline; quality/freshness phản ánh đúng corruption log.
- **Kết quả thực tế:** baseline `hit_rate 1.000` / `token_f1 1.000`; corrupted `0.667` / `0.671`, quality 6/11, `is_fresh false`; repaired về đúng baseline trên toàn bộ metric. Unit test 8/8 pass.
- **Artifact/log:** `data/results/`, `data/quality/`, `data/reports/`. Không chứa secret.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** baseline cho kết quả 1.000 trên mọi metric. Câu hỏi là con số đó có phản ánh chất lượng hệ thống không.
- **Các phương án đã cân nhắc:** (1) giữ nguyên và báo cáo 1.000 như thành tích; (2) viết `ground_truth` theo lối diễn giải để metric "có vẻ thực tế" hơn; (3) giữ test set chính, thêm một probe set riêng để đo tầng retrieval.
- **Phương án đã chọn:** (3), kèm nói thẳng trong báo cáo rằng 1.000 là hệ quả của thiết kế.
- **Lý do:** phương án (2) sai về đo lường — vì `_extract_answer` trả nguyên văn metadata, ground truth diễn giải sẽ khiến hệ thống **trả lời đúng** vẫn bị `token_f1` thấp, và ở CP5 không phân biệt được "giảm vì corruption" với "giảm vì ground truth không khớp cách trả lời". Probe set giải quyết đúng vấn đề: câu hỏi do LLM diễn đạt lại từ abstract, **cấm nhắc title** (vì title trong dấu nháy đơn sẽ kích hoạt exact lookup), nên semantic search buộc phải làm việc thật.
- **Bằng chứng quyết định phù hợp:** probe cho baseline `hit@4 0.868`, `top1 0.789`, `MRR 0.825` — có headroom thật, và ở corrupted tụt xuống `0.763 / 0.632 / 0.686`. Bộ lọc tự động loại 10/48 câu hỏi mà LLM vẫn lén nhắc title, chứng tỏ nếu không kiểm thì probe đã bị vô hiệu. Chi phí: LLM chỉ gọi một lần lúc sinh, lúc evaluate không cần LLM.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** baseline `mean_token_f1` bằng `0.750` thay vì `1.000`, trong khi `retrieval_hit_rate` vẫn `1.000`. Tách theo loại câu hỏi: `summary/authors/categories` đều `1.00`, riêng `date` bằng `0.00` ở cả 6 sample.
- **Lệnh tái hiện:** `python script/run_phase1.py` rồi đọc `data/results/baseline_answers.json`.
- **Nguyên nhân gốc:** `published` không được chuẩn hoá thành chuỗi trong cleaned dataframe. Test set build từ CSV nên ground truth là `'2026-08-01 00:00:00+00:00'`; còn index build từ dataframe in-memory (dtype datetime64) nên metadata là `'2026-08-01T00:00:00+00:00'`. Cùng một dữ liệu, hai cách render, khác nhau đúng một ký tự phân cách. Token F1 = 0 vì **định dạng**, không phải vì chất lượng dữ liệu. Đây cũng chính là vấn đề tôi đã nêu từ CP1 nhưng chưa được sửa tận gốc.
- **Cách xử lý:** rebuild baseline index từ dataframe đọc lại từ CSV — cùng đường đi với test set; đồng thời trong `corruption_flow.py` cũng đọc lại repaired data từ CSV trước khi evaluate.
- **Cách xác minh sau khi sửa:** baseline `mean_token_f1` về `1.000`, `date` về `1.00`; repaired cũng từ `0.750` lên `1.000`.
- **Điều học được:** hai artifact "cùng dữ liệu" vẫn có thể lệch nếu đi qua hai đường serialize khác nhau. Ground truth và index metadata bắt buộc phải sinh từ cùng một biểu diễn.

Phần chưa xử lý triệt để:

- **Phạm vi bị ảnh hưởng:** bất kỳ ai chạy lại `phase1.py` mà không rebuild index từ CSV sẽ lại ghi đè baseline bằng `mean_token_f1 = 0.750`.
- **Những gì đã loại trừ:** không phải lỗi retrieval (`hit_rate` vẫn 1.000), không phải lỗi test set (3 loại câu hỏi kia đều đúng), không phải lỗi judge.
- **Bước tiếp theo:** cleaning ghi `published` dạng chuỗi `YYYY-MM-DD` trong chính dataframe; khi đó CSV và in-memory giống hệt nhau và cả lớp lỗi này biến mất.

## 7. Hiểu biết về luồng end-to-end

1. **Crossref → vector index:** `crossref.py` gọi Crossref REST API với `query`/`filter`/`rows` từ `Settings`, lưu raw response và parse thành `PaperRecord` vào `data/raw/`. `cleaning.py` chuẩn hoá text (bỏ JATS/HTML entity), parse ngày nhiều độ chính xác, dedupe theo `paper_id`, tính `age_days` và ghép `text_for_embedding`. `index.py` embed cột đó bằng MiniLM và ghi vào collection Chroma kèm metadata phẳng.

2. **Test set và ground-truth doc IDs:** mỗi paper sinh 4 câu hỏi, `ground_truth` copy nguyên văn trường metadata tương ứng, `ground_truth_doc_ids` là `paper_id` của chính row đó. Khi evaluate, `retrieval_hit` kiểm tra gold ID có nằm trong top-k retrieved không — đo **tầng retrieval**; `token_f1` so answer với ground truth — đo **tầng answer**; LLM judge bắt trường hợp đúng nghĩa nhưng khác chữ.

3. **Quality khác freshness:** quality checks hỏi "dataset này có đúng schema và toàn vẹn không" (null, unique, duplicate, độ dài) — đo tại một thời điểm. Freshness hỏi "dữ liệu này còn mới không" — so `age_days` với ngưỡng 180 ngày. Một dataset có thể sạch hoàn hảo mà vẫn cũ, và ngược lại.

4. **Vì sao phải dùng cùng test set:** nếu mỗi trạng thái sinh test set riêng thì câu hỏi, ground truth và độ khó đều khác nhau, chênh lệch metric không còn quy được về corruption. Test set được khoá từ baseline và ba trạng thái dùng chung đúng một file.

5. **Repair thành công dựa trên gì:** delta giữa repaired và baseline bằng 0 trên `retrieval_hit_rate`, `mean_token_f1`, probe `MRR`; quality trở lại 11/11 và `is_fresh` về `true`. Chỉ khi cả metric lẫn quality/freshness cùng về mốc baseline mới được gọi là phục hồi.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.000 | 0.667 | 1.000 | Giảm đúng bằng 8/24 câu mất gold document do 2 record bị drop |
| `mean_token_f1` | 1.000 | 0.671 | 1.000 | Bị `categories` kéo lên giả tạo, xem phân tích dưới |
| `judge_accuracy` | 1.000 | 0.625 | 1.000 | LLM judge thật, fallback 0/24 ở cả ba trạng thái |
| `mean_judge_score` | 5 | 3.708 | 5 | Judge chấm thấp ngay cả khi answer có vẻ trôi chảy |
| Quality checks | 11/11 | 6/11 | 11/11 | Fail: `paper_id_unique`, `duplicate_records`, `summary_not_null`, `summary_min_chars`, `freshness_age_days` |
| Freshness status | true | false | true | `stale_rows` 0 → 3, `max_age_days` 174 → 2067 |
| Probe `top1` / `MRR` | 0.789 / 0.825 | 0.632 / 0.686 | 0.789 / 0.825 | Thước đo retrieval thuần, không bị exact lookup che |

### Kết luận từ số liệu

1. Drop 2 record mới nhất (`corruption_log.json`) → 8/24 câu hỏi mất gold document → `retrieval_hit_rate` xuống đúng `16/24 = 0.667`, và `summary` token F1 sập từ `1.00` xuống `0.18`.
2. Repair chạy lại cleaning từ `data/raw/crossref_records.json` → quality về 11/11, `is_fresh` về `true`, `stale_rows` về 0 → toàn bộ metric về đúng baseline, delta bằng 0.

Corruption nào ảnh hưởng rõ nhất và vì sao?

`drop_latest_record` — vì nó xoá hẳn document khỏi index nên không cách nào retrieval đúng được, và toàn bộ mức giảm `retrieval_hit_rate` quy về đúng corruption này. Blank/noise summary xếp sau: document vẫn còn nhưng nội dung trả lời sai. Ví dụ rõ nhất là `10.1111/exsy.70341::summary`: document bị xoá, retrieval trả về một paper RAG khác, và agent trả lời trôi chảy bằng summary của paper sai (`token_f1 0.194`, judge 2/5). Bài học thực tế: **data hỏng không làm agent báo lỗi, nó làm agent sai một cách tự tin.**

Kết quả nào khác với kỳ vọng ban đầu?

Hai kết quả.

Thứ nhất, `categories` giữ nguyên `token_f1 = 1.00` ở corrupted **dù `hit_rate` chỉ 0.667**. Nghĩa là 8 câu retrieval trả về sai paper mà đáp án vẫn đúng — bởi Crossref không trả field `subject` nên cả 24 paper đều có `categories_joined = "Uncategorized"`. Loại câu hỏi này không mang tín hiệu và đang kéo `mean_token_f1` lên cao hơn thực tế; nếu bỏ nó, mức sụt của corrupted còn sâu hơn 0.671.

Thứ hai, `truncate_title` **không làm fail bất kỳ check nào** trong 11 check (title ngắn đi chứ không rỗng), nhưng vẫn góp phần kéo probe MRR từ `0.825` xuống `0.686`. Tôi đã dự đoán điều này từ CP0 và số liệu xác nhận đúng. Cả hai đều dẫn tới cùng một kết luận: **quality check pass không có nghĩa dữ liệu sạch, nếu check không nhìn đúng chỗ.**

Giới hạn của kết luận: test set chỉ 24 sample; corruption chọn row từ đầu dataframe mà test set cũng ưu tiên paper mới nhất nên cả 6/6 paper test set đều bị đụng — tác động đo được là **cận trên**, không phải mức trung bình. Repair thành công **vì raw snapshot còn nguyên**; nếu hỏng từ tầng raw thì không có điểm khôi phục nào, và kịch bản đó chưa được kiểm chứng.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** clean data, index và test set phải sinh từ **cùng một snapshot**. Trong lab này cả ba đã lệch nhau hai lần — một lần do cleaning strip markup mà index chưa rebuild, một lần do `published` render khác nhau giữa CSV và in-memory — và cả hai lần đều làm metric sai theo hướng dễ tưởng nhầm là lỗi chất lượng dữ liệu.
2. **Data quality/observability:** một check pass chỉ chứng minh đúng cái nó đo. `truncate_title` không bị bắt bởi check nào; `NaN` trong `age_days` từng lọt qua check freshness vì trong pandas `NaN > threshold` luôn là `False`. Phải chủ động hỏi "lỗi nào sẽ lách qua bộ check này" thay vì hài lòng với 11/11 PASS.
3. **Ảnh hưởng của data lên RAG agent:** hệ thống không hề báo lỗi khi dữ liệu hỏng — nó vẫn trả lời đầy đủ, chỉ là sai. Nếu không có ground truth và metric thì không ai phát hiện được.

### Nếu có thêm thời gian

Thêm một quality check phát hiện ngôn ngữ. Khi phân tích 5 miss của probe set, 4 miss đến từ hai paper **tiếng Nga và tiếng Indonesia** — corpus đa ngữ nhưng `all-MiniLM-L6-v2` chỉ mạnh tiếng Anh nên embedding câu hỏi tiếng Anh không gần document đó. Cả hai paper này qua sạch 11/11 check vì summary dài, ngày hợp lệ, `text_for_embedding` không rỗng. Tôi có thử đo bằng tỉ lệ ký tự ASCII nhưng chỉ bắt được paper tiếng Nga; paper tiếng Indonesia dùng bảng chữ Latin nên lọt lưới — nên tôi ghi lại như một hạn chế đã biết thay vì vá bằng heuristic sai. Cách đo cải thiện: thêm `language_detected` vào quality report, rồi so probe `MRR` của nhóm document cùng ngôn ngữ với nhóm khác ngôn ngữ.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Lê Huy Hoàng
**Ngày xác nhận:** 2026-08-06
