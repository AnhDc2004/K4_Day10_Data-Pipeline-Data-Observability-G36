# Báo cáo cá nhân — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Phan Văn Phương |
| MSSV | 2A202602033 |
| Khóa/Lớp | K4 |
| Tên nhóm | G36 |
| Vai trò chính | Vai trò 4 — RAG & Agent owner |
| Repository | `K4_Day10_Data-Pipeline-Data-Observability-G36` |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Retrieval contract và Chroma index | `src/retrieval/index.py`, `src/retrieval/contract.py` | Clean dataframe | Baseline/corrupted/repaired manifest và collection riêng | Hoàn thành |
| Embedding và agent smoke test | `src/retrieval/embeddings.py`, `src/retrieval/agent.py`, `script/run_retrieval_cp*.py` | `text_for_embedding`, OpenRouter config | Search/lookup evidence và agent tool trace | Hoàn thành |
| Baseline/corrupted/repaired verification | `script/run_retrieval_cp3.py`, `script/run_retrieval_cp5.py`, `script/run_retrieval_cp6.py` | Index manifest, clean data, test set | `report/role4_cp4_cp5.md`, `report/role4_cp6.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Debug handoff và lỗi runtime | `phase1.py`, evaluator, role Lead | Xác định path raw lệch tên, Timestamp metadata lỗi, Ragas model type lỗi và giới hạn OpenRouter quota. |
| Kiểm tra portability | Các artifact trong `data/embeddings/` và `data/chroma/` | Manifest dùng path tương đối; `load()` dùng path Chroma của checkout hiện tại. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Khóa retrieval contract và baseline | `LocalEmbeddingIndex`, `papers_embeddings.json`, `papers-baseline` | 24 documents, MiniLM + Chroma, `top_k=4` | `run_retrieval_cp3.py`, manifest audit |
| Xác minh corrupted index | `papers_embeddings_corrupted.json`, `papers-corrupted` | 23 documents; baseline vẫn 24 documents | `run_retrieval_cp5.py`, report CP4/CP5 |
| Xác minh repaired index và agent | `papers_embeddings_repaired.json`, `papers-repaired` | 24 documents; test set không thiếu ID/title; agent có 1 tool message | `run_retrieval_cp6.py`, report CP6 |
| Regression và metadata portability | `tests/test_retrieval_contract.py`, `src/retrieval/llm.py` | 11/11 unit tests PASS; provider request có timeout | `python -m unittest discover -s tests -q` |

Output tiêu biểu: `papers-repaired` có 24 documents, manifest audit PASS, test-set verification PASS và factual agent query trả lời với 1 tool message.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Role 4 đảm bảo dữ liệu clean có thể chuyển thành embedding index tái lập được, truy hồi đúng tài liệu và agent phải lấy context qua tool. Khi chạy corruption/repair, mỗi trạng thái phải có collection và manifest riêng để baseline không bị ghi đè.

### Cách triển khai

`LocalEmbeddingIndex.build()` tạo document có `record_id`, `paper_id`, title, content và metadata tối thiểu, sau đó embed `text_for_embedding` bằng `sentence-transformers/all-MiniLM-L6-v2` và lưu vào Chroma. Manifest ghi `persist_path` tương đối. `load()` không tin path từ máy build mà dùng `settings.paths.chroma_dir` của checkout hiện tại.

Metadata pandas như `Timestamp`, `NaN` và NumPy scalar được chuyển thành giá trị Chroma/JSON hợp lệ. Với corrupted duplicate, `record_id` có thêm row index nên index vẫn lưu được hai document, trong khi quality contract vẫn phát hiện duplicate `paper_id`.

Agent được tạo với hai tool: semantic search và exact paper lookup. Factual question được kiểm tra bằng tool message và collection đang được xác minh, không chỉ bằng việc answer có nội dung.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Clean dataframe có `paper_id`, `title`, `summary`, `authors_joined`, `categories_joined`, `published`, URL và `text_for_embedding`. |
| Output | Chroma collections `papers-baseline`, `papers-corrupted`, `papers-repaired` và ba manifest tương ứng. |
| Module phụ thuộc | `src/core/config.py`, `src/ingestion/cleaning.py`, `src/evaluation/testset.py`, `src/retrieval/embeddings.py`. |
| Module sử dụng output | `src/retrieval/qa.py`, `src/retrieval/agent.py`, evaluator và pipeline orchestration. |
| Điều kiện lỗi cần xử lý | Metadata Timestamp/NaN, duplicate ID, manifest path tuyệt đối, collection sai tên, test-set title/ID không lookup được và provider timeout/quota. |

### Cách xác minh

```powershell
.venv\Scripts\python.exe script\run_retrieval_cp3.py
.venv\Scripts\python.exe script\run_retrieval_cp5.py
.venv\Scripts\python.exe script\run_retrieval_cp6.py
.venv\Scripts\python.exe -m unittest discover -s tests -q
git diff --check
```

- **Kết quả mong đợi:** Manifest/collection đúng tên, document count khớp dataframe, test set không missing, search/lookup có kết quả và agent có tool message.
- **Kết quả thực tế:** Baseline 24 docs, corrupted 23 docs, repaired 24 docs; CP6 PASS; agent có 1 tool message; 11/11 tests PASS.
- **Artifact/log:** `report/role4_cp4_cp5.md`, `report/role4_cp6.md`, `data/embeddings/papers_embeddings*.json`, `data/results/repair_validation.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Manifest có thể được tạo trên một máy Windows rồi chạy trên checkout khác.
- **Các phương án đã cân nhắc:** Tin vào absolute `persist_path` trong manifest; hoặc ghi path tương đối và resolve bằng settings local khi load.
- **Phương án đã chọn:** Dùng path tương đối như `data\\chroma`; `LocalEmbeddingIndex.load()` luôn dùng `settings.paths.chroma_dir`.
- **Lý do:** Không phụ thuộc drive/path của máy build, giảm lỗi khi pull hoặc chạy trên máy thành viên khác; collection name vẫn được lấy từ manifest contract.
- **Bằng chứng:** Manifest audit CP3/CP5/CP6 đều báo `persist_path_portable: true` và load được baseline/corrupted/repaired collection.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `Expected metadata value to be a str, int, float, bool, SparseVector, list, or None, got ... Timestamp in add.`
- **Lệnh hoặc bước tái hiện:** Build `LocalEmbeddingIndex` từ clean dataframe có cột `published` kiểu pandas `Timestamp`.
- **Nguyên nhân gốc:** Chroma không nhận pandas `Timestamp` trực tiếp trong metadata.
- **Cách xử lý:** Thêm `_metadata_value()` để chuyển missing value, Timestamp/date/datetime và NumPy scalar thành giá trị JSON/Chroma-safe; thêm `allow_nan=False` trước khi ghi manifest.
- **Cách xác minh sau khi sửa:** `python -m unittest discover -s tests -q` → 11 tests PASS; baseline/corrupted/repaired index build và load thành công.
- **Điều học được:** Dataframe có thể hợp lệ với pandas nhưng vẫn vi phạm kiểu dữ liệu của vector store; cần kiểm tra contract ở boundary.

Blocker đã ghi nhận nhưng không che kết quả:

- Ragas từng nhận `SentenceTransformer` object ở trường `model`, trong khi telemetry yêu cầu string; đã giữ model nội bộ ở `_model` và expose model name dạng string.
- Một lần agent smoke bị OpenRouter HTTP 403 do quota/key limit; sau khi quota được cấp lại, CP6 chạy PASS. Request timeout 30 giây được thêm vào `src/retrieval/llm.py`.

## 7. Hiểu biết về luồng end-to-end

1. Crossref response được lưu thành raw snapshot/records. Role cleaning chuẩn hóa field, loại record không có ID/title, dedupe và tạo `text_for_embedding`. Role 4 embed text bằng MiniLM rồi lưu document và metadata vào Chroma.
2. Evaluation set chứa question, ground truth và `ground_truth_doc_ids`. Retrieval hit khi một document ID được truy hồi thuộc danh sách ground truth; answer tiếp tục được đo bằng token F1 và judge.
3. Quality checks kiểm tra cấu trúc và nội dung dữ liệu như row count, null, duplicate, summary và embedding text. Freshness theo dõi tính thời gian của `published`/`age_days` so với threshold.
4. Baseline, corrupted và repaired phải dùng cùng test set để thay đổi metric phản ánh dữ liệu/index, không phản ánh việc đổi câu hỏi.
5. Repair được kiểm chứng trước hết bằng `repair_validation.json`: row count, ID, schema, duplicate, summary, noise, date và embedding text được phục hồi. Sau đó repaired quality/freshness đều 11/11 và fresh; metric agent chỉ được kết luận khi evaluator tạo artifact tương ứng.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.000 | Chưa có artifact | Chưa có artifact | Baseline evaluator có 24/24 hits; corrupted/repaired evaluator chưa bàn giao JSON. |
| `mean_token_f1` | 0.750 | Chưa có artifact | Chưa có artifact | Không suy diễn metric từ smoke search. |
| `judge_accuracy` | 1.000 | Chưa có artifact | Chưa có artifact | Baseline report có fallback/Ragas limitation cần đối chiếu khi evaluator chạy. |
| `mean_judge_score` | 5.000 | Chưa có artifact | Chưa có artifact | Không trình bày như kết quả LLM judge cho trạng thái chưa có file. |
| Quality checks | 11/11 PASS | Chưa có artifact | 11/11 PASS | Repair validation và repaired quality đều PASS. |
| Freshness status | PASS | Chưa có artifact | PASS | Baseline/repaired `max_age_days=174`, threshold 180. |

### Kết luận từ số liệu

1. Corruption log tạo `drop_latest`, `missing_summary`, noise, old date và duplicate → corrupted clean còn 23 rows và duplicate ID bị contract phát hiện; corrupted metrics/quality chưa có artifact nên chưa kết luận mức giảm agent metric.
2. Repair từ `data/raw/crossref_records.json` → 24 rows, ID/schema/summary/noise/date/duplicate/embedding được phục hồi → repaired quality 11/11, freshness PASS, manifest audit và test-set verification PASS; metric recovery chưa thể khẳng định cho tới khi evaluator ghi `repaired_metrics.json`.

Corruption rõ nhất ở tầng retrieval là `drop_latest`, vì làm mất trực tiếp hai document khỏi corrupted collection. Duplicate cũng quan trọng vì làm quality contract fail dù Chroma vẫn có thể lưu document bằng `record_id` khác nhau. Hai nhận định này dựa trên `corruption_log.json` và collection counts, không phải metric evaluator.

Kết quả chưa đủ để kết luận corrupted agent kém hơn baseline vì `corrupted_metrics.json`, `corrupted_answers.json`, `repaired_metrics.json` và `repaired_answers.json` chưa tồn tại trong checkout hiện tại. Smoke retrieval của role 4 chỉ chứng minh collection và contract, không thay thế evaluator.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Retrieval artifact phải được sinh từ cùng clean snapshot với test set; chỉ khác newline, markup hoặc path cũng có thể làm audit/lookup sai.
2. Quality và freshness là tín hiệu độc lập: duplicate/content loss có thể bị phát hiện bởi quality, còn old date cần freshness; không nên dùng một signal để đại diện cho tất cả lỗi dữ liệu.
3. Agent answer có ý nghĩa hơn khi trace chứng minh tool đã gọi đúng collection; CP6 repaired query có answer và 1 tool message nhưng metric đầy đủ vẫn cần evaluator.

### Nếu có thêm thời gian

Hoàn thiện evaluator corruption/repaired và comparison report với cùng test set, sau đó đo Recall/Hit rate, token F1, judge và Ragas trên ba trạng thái. Đồng thời thêm test để bảo đảm corruption flow không ghi đè các manifest/collection baseline.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phan Văn Phương
**Ngày xác nhận:** 2026-08-06
