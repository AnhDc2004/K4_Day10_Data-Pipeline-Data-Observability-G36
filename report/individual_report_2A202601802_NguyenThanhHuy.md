# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Thành Huy |
| MSSV | 2A202601802 |
| Khóa/Lớp | K4 |
| Tên nhóm | G36 |
| Vai trò chính | Role 2 — Ingestion owner (Crossref + raw lineage) |
| Repository | https://github.com/AnhDc2004/K4_Day10_Data-Pipeline-Data-Observability-G36 |
| Ngày hoàn thành | 2026-08-07 |

## 2. Vai trò và phạm vi công việc

Phạm vi theo bảng phân công nhóm 5 người: `src/ingestion/crossref.py` · `data/raw/` — lấy dữ liệu từ Crossref và giữ mạch truy vết từ nguồn tới mọi tầng phía sau.

Vai trò này là điểm bắt đầu của toàn bộ pipeline, nên phần lớn giá trị của nó không nằm ở số dòng code mà ở hai cam kết: **snapshot không đổi giữa ba trạng thái** (baseline / corrupted / repaired) và **mọi bản ghi ở tầng sau đều truy ngược được về nguồn**. Nếu một trong hai cam kết vỡ, phần so sánh metric của cả nhóm mất ý nghĩa.

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Lineage trace 4 tầng | `script/p2_checks/cp2_lineage_trace.py` | `paper_id` bất kỳ | Xác nhận bản ghi đi liền mạch raw response → raw records → clean → index | Hoàn thành |
| Truy xuất bằng chứng nguồn | `script/p2_checks/cp2_source_attribution.py` | `paper_id` | Bằng chứng raw + clean, kèm cờ lệch giữa hai tầng | Hoàn thành |
| Xác minh raw + vân tay toàn vẹn | `script/p2_checks/cp3_verify_raw.py` | `data/raw/*.json` | `data/quality/p2_raw_integrity.json` (sha256 hai file raw) | Hoàn thành |
| Đối chiếu raw ↔ clean count | `script/p2_checks/cp3_compare_counts.py` | raw records, `papers_clean.csv`, `cleaning_report.json` | Chứng minh chênh lệch 0 dòng là có căn cứ, không phải trùng hợp | Hoàn thành |
| Audit không fetch lại nguồn | `script/p2_checks/cp3_no_refetch_audit.py` | `src/`, biến môi trường, vân tay raw | Xác nhận baseline/corrupted/repaired chạy trên cùng snapshot | Hoàn thành |
| Kiểm tra tiền corruption | `script/p2_checks/cp5_pre_corruption_check.py` | vân tay raw, `corruption_log.json` | Xác nhận raw nguyên vẹn + corruption ghi ra path riêng | Hoàn thành |
| Bằng chứng phục hồi theo bản ghi | `script/p2_checks/cp6_repair_lineage_proof.py` | 3 dataset + `corruption_log.json` | 24/24 kiểm tra đạt ở mức từng bản ghi | Hoàn thành |

> **Ghi chú ownership cần chốt với VT1 trước khi nộp:** `git log -- src/ingestion/crossref.py` cho thấy hai commit `208cf1e` ("hoàn thiện crossref") và `629a6ef` ("thay đổi crossref") đứng tên VT1 (Đinh Đức Anh). Bản `crossref.py` đang có trong repo vì vậy **không phải commit trực tiếp của tôi**, và tôi không ghi nó vào bảng trên. Hai bên cần thống nhất phần nào là đóng góp của ai và sửa dòng tương ứng ở [báo cáo nhóm §5](group_report.md) — theo đúng tiền lệ VT1 đã làm với VT5 về `corruption_flow.py`. Phần tôi nhận ownership là **tầng xác minh và lineage**, không phải phần implement fetch/parse.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Phát hiện `data/chroma/chroma.sqlite3` bị `.gitignore` trong khi 21 file `.bin` của HNSW vẫn được commit | VT4 — `src/retrieval/index.py`, `data/chroma/` | Index không load được trên bản clone sạch (`list_collections()` trả rỗng), các file `.bin` đã commit là mồ côi. Không chặn vì `phase1.py` tự build lại index, nhưng thuộc mục trừ điểm "commit thiếu file quan trọng" |
| Đối chiếu `record_ids` trong `corruption_log.json` với raw snapshot | VT3 — `src/ingestion/corruption.py` | Xác nhận 7/7 bản ghi bị corrupt đều truy được về raw, tức mọi kịch bản corruption đều repair được — bằng chứng cho kết luận §11 của báo cáo nhóm |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| CP2 — truy vết `paper_id` xuyên 4 tầng | `cp2_lineage_trace.py` | 4/5 tầng đạt; tầng index `[SKIP]` trên clone sạch (xem §6) | `python script/p2_checks/cp2_lineage_trace.py` |
| CP3 — xác minh raw đọc được, ghi vân tay | `cp3_verify_raw.py` → `data/quality/p2_raw_integrity.json` | 7/7 đạt; 24 item ↔ 24 record, 0 DOI thất lạc | `python script/p2_checks/cp3_verify_raw.py` |
| CP3 — so sánh raw/clean count | `cp3_compare_counts.py` | 4/4 đạt; chênh lệch 0 dòng, khớp `cleaning_report.json` | `python script/p2_checks/cp3_compare_counts.py` |
| CP3 — audit không fetch lại nguồn | `cp3_no_refetch_audit.py` | 6/6 đạt; 1 vị trí gọi mạng duy nhất, có guard | `python script/p2_checks/cp3_no_refetch_audit.py` |
| CP5 — raw nguyên vẹn, corruption cô lập | `cp5_pre_corruption_check.py` | 6/6 đạt; sha256 raw không đổi sau corruption flow | `python script/p2_checks/cp5_pre_corruption_check.py` |
| CP6 — chứng minh phục hồi từng bản ghi | `cp6_repair_lineage_proof.py` | 24/24 đạt | `python script/p2_checks/cp6_repair_lineage_proof.py` |

Một output cụ thể phần việc của tôi tạo ra:

`data/quality/p2_raw_integrity.json` ghi sha256 của hai artifact raw. Nhờ mốc này, sau khi chạy `run_corruption_flow.py` tôi chứng minh được `crossref_response.json` giữ nguyên `de97b5f9…` và `crossref_records.json` giữ nguyên `f72a5f9b…`. Đây là bằng chứng **duy nhất** cho thấy corruption flow thực sự không chạm vào nguồn — ba mục kiểm tra tĩnh còn lại (quét `src/`, kiểm guard, kiểm biến môi trường) chỉ chứng minh code *không có đường dẫn tới* việc fetch, chứ không chứng minh nó *đã không* fetch.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Repair của bài lab này định nghĩa là "chạy lại cleaning từ nguồn đáng tin", không phải "sửa tay dữ liệu hỏng". Định nghĩa đó chỉ đứng vững nếu có một điểm khôi phục thật sự bất biến. Câu hỏi tôi phải trả lời được bằng artifact, không bằng lời: **làm sao biết `data/raw/` chưa từng bị đụng tới giữa baseline và repaired?**

Kèm theo là câu hỏi thứ hai: khi metric tụt, làm sao phân biệt "RAG kém" với "dữ liệu vào đã sai từ khâu parse"?

### Cách triển khai

Ba lớp, đi từ yếu tới mạnh:

1. **Lớp cấu trúc** — `cp3_verify_raw.py` đọc raw response theo đúng đường dẫn `message.items[]` thay vì đoán, đối chiếu tập DOI ở response với tập `paper_id` ở records. Đây là chỗ bắt được lỗi parse làm rơi bản ghi.
2. **Lớp guard** — `cp3_no_refetch_audit.py` xác minh `phase1.py` chỉ gọi `fetch_source_records` khi thiếu snapshot **hoặc** `refresh_source=True`, và `corruption_flow.py` không hề tham chiếu tới hàm này. Lớp này chứng minh *không có đường dẫn code* tới việc fetch.
3. **Lớp vân tay** — sha256 hai file raw, ghi ra artifact, so lại sau mỗi pha. Lớp này chứng minh *sự việc đã không xảy ra*, chứ không phải nó *không thể xảy ra*.

Chỉ lớp 3 là bằng chứng thật; hai lớp trên là lập luận. Tôi giữ cả ba vì lớp 1–2 chỉ ra **chỗ nào** hỏng khi lớp 3 báo đỏ.

Về chuẩn hoá định danh: `paper_id` được hạ chữ thường ngay khi parse (`raw_doi.strip().lower()`). Mọi so khớp giữa các tầng trong bộ kiểm tra của tôi đều dựa vào giả định này, nên `cp3_verify_raw.py` kiểm tra lại nó như một invariant thay vì tin.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `data/raw/crossref_response.json` (payload nguyên trạng), `data/raw/crossref_records.json` (24 `PaperRecord`), `data/clean/papers_clean*.csv`, `data/results/corruption_log.json` |
| Output | `data/quality/p2_raw_integrity.json`; exit code 0/1 của 7 script kiểm tra |
| Module phụ thuộc | `core.load_settings` (mọi path lấy từ `Settings`, không hard-code) |
| Module sử dụng output | Không module nào trong đường chạy pipeline — bộ kiểm tra chạy độc lập sau pipeline, nên không thể vô tình đổi artifact của nhóm |
| Điều kiện lỗi cần xử lý | Thiếu `chroma.sqlite3` trên clone sạch; chưa chạy `run_corruption_flow.py`; console Windows cp1252 làm chết script khi in tiếng Việt |

### Cách xác minh

```bash
python script/p2_checks/cp3_verify_raw.py
python script/p2_checks/cp3_no_refetch_audit.py
python script/p2_checks/cp6_repair_lineage_proof.py
```

- **Kết quả mong đợi:** raw snapshot giữ nguyên sha256 qua cả ba pha; mọi bản ghi bị corrupt quay lại đúng nguyên trạng ở repaired.
- **Kết quả thực tế:** 7/7, 6/6 và 24/24 kiểm tra đạt. Cụ thể ở CP6: 2 bản ghi bị `drop_latest` quay lại đủ, summary rỗng phục hồi đủ 1869 ký tự, title bị cắt từ 15 ký tự phục hồi về 110 ký tự, `published` bị đẩy lùi 730 ngày quay về `2026-04-07`, bản duplicate còn đúng 1 dòng; 5 trường `title`/`summary`/`published`/`authors_joined`/`text_for_embedding` khớp 100% trên cả 24 dòng.
- **Artifact/log:** `data/quality/p2_raw_integrity.json`. Không chứa secret — chỉ có tên file, sha256 và số đếm.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** chọn field nào làm `paper_id`. Định danh này là khoá nối toàn bộ pipeline: ground truth trong test set, ID document trong Chroma, `record_ids` trong corruption log đều dựa vào nó. Đổi nó về sau nghĩa là phải dựng lại index và khoá lại test set.
- **Các phương án đã cân nhắc:**
  1. Số thứ tự trong response (`paper-0`, `paper-1`…) — đơn giản nhất.
  2. Hash của title.
  3. DOI hạ chữ thường.
- **Phương án đã chọn:** DOI hạ chữ thường.
- **Lý do:** phương án 1 không ổn định qua các lần fetch — Crossref xếp hạng theo độ liên quan nên cùng một query ở hai thời điểm cho thứ tự khác nhau, và khi đó `ground_truth_doc_ids` trong test set trỏ sai bài mà không có dấu hiệu nào báo lỗi. Phương án 2 ổn định hơn nhưng vỡ ngay khi title được chuẩn hoá, và nó chính là trường mà kịch bản `truncate_title` ở CP5 làm hỏng — định danh không được phép phụ thuộc vào trường có thể bị corrupt. DOI là khoá do nhà xuất bản cấp, bất biến, và cho phép truy ngược ra ngoài hệ thống qua `https://doi.org/{id}`.
- **Bằng chứng quyết định phù hợp:** ở CP5, kịch bản `truncate_title` cắt title của `10.20944/preprints202602.0996.v1` từ 110 xuống 15 ký tự. Bản ghi vẫn được nhận diện đúng ở cả ba trạng thái và repair khôi phục chính xác — nếu `paper_id` dẫn xuất từ title thì bản ghi này đã thành một document lạ và corruption log sẽ mất dấu nó.

## 6. Một lỗi hoặc blocker đã xử lý

### Lỗi đã xử lý — kiểm tra không bao giờ báo đỏ

- **Triệu chứng:** script `P2_cp3_task3_check.py` của tôi luôn in `[OK] Tuyệt vời! Không phát hiện lệnh gọi mạng/fetch dữ liệu ngoài nào trong mã nguồn` — kể cả khi tôi cố tình thêm `requests.get` vào một file trong `src/` để thử.
- **Bước tái hiện:** `python P2_cp3_task3_check.py` từ thư mục gốc, sau khi thêm một dòng `requests.get(...)` bất kỳ vào `src/ingestion/cleaning.py`.
- **Nguyên nhân gốc:** phép quét là `Path(".").glob("*.py")`. `glob` không đệ quy, nên nó chỉ liệt kê file `.py` ở **thư mục gốc** — mà toàn bộ code thật nằm trong `src/`. Danh sách file quét được là rỗng, vòng lặp không chạy lần nào, `suspicious_findings` rỗng, và nhánh "không phát hiện gì" luôn được chọn. Kiểm tra không sai logic; nó chỉ chưa bao giờ đọc file nào.
- **Cách xử lý:** đổi sang `(project_dir / "src").rglob("*.py")`. Nhưng khi quét đúng thì `crossref.py` lộ ra `requests.get` — và đó là lệnh **hợp lệ**, vì đó chính là việc của module ingestion. Nên tôi đổi luôn tiêu chí: không hỏi "có lệnh gọi mạng không" mà hỏi "lệnh gọi mạng có nằm ngoài `crossref.py` không" và "nó có bị guard chặn không", rồi bổ sung lớp vân tay sha256 làm bằng chứng thực nghiệm.
- **Cách xác minh sau khi sửa:** `python script/p2_checks/cp3_no_refetch_audit.py` → 6/6 đạt, và mục 1 in ra đúng vị trí `crossref.py:138`, chứng tỏ phép quét thực sự đọc được file.
- **Điều học được:** một kiểm tra chưa từng báo đỏ thì chưa được xem là kiểm tra. Trước khi tin một check màu xanh, phải làm nó đỏ ít nhất một lần bằng lỗi giả. Đây cũng là lý do tôi để `cp2_lineage_trace.py` trả exit code 1 khi tầng index `[SKIP]` thay vì lặng lẽ bỏ qua — bỏ qua sẽ biến nó thành đúng loại check vô dụng vừa nói.

### Blocker chưa xử lý — `categories` rỗng trên toàn bộ 24 bản ghi

- **Phạm vi bị ảnh hưởng:** `src/ingestion/crossref.py:62-64` → `data/raw/crossref_records.json` → `categories_joined` trong `data/clean/` → 6/24 sample loại `categories` trong `data/eval/test_set.json`.
- **Triệu chứng:** cả 24 bản ghi có `categories: []`, kéo theo `primary_category = "Uncategorized"` và `categories_joined = "Uncategorized"` cho toàn bộ dataset.
- **Nguyên nhân gốc:** parser đọc field `subject` của Crossref, nhưng **0/24 item trong `crossref_response.json` có field này** — Crossref chỉ trả `subject` cho một phần publisher, và không publisher nào trong kết quả của query này cung cấp. Đây không phải lỗi code: parser xử lý đúng trường hợp thiếu field, chỉ là fallback `"Uncategorized"` áp cho 100% dữ liệu nên trường này mất hết sức phân biệt.
- **Những gì đã loại trừ:** không phải lỗi parse (đã kiểm tra trực tiếp trong `crossref_response.json`, field không tồn tại); không phải do cleaning làm mất (raw records đã rỗng sẵn); không phải do `source_filter` (`has-abstract:true` không lọc theo subject).
- **Hệ quả đo lường:** 6 câu hỏi loại `categories` trong test set được trả lời đúng bằng chữ "Uncategorized" cho **bất kỳ** paper nào được retrieve. Nghĩa là 1/4 test set không đo được chất lượng retrieval — trả lời sai bài vẫn ra đúng chữ. VT5 đã nêu rủi ro này từ [CP1 B4](cp1_eval_observability.md) và nhắc lại ở [CP5 §5](cp5_cp6_eval_observability.md#L107); tôi xác nhận nguyên nhân nằm ở tầng ingestion, tức phạm vi của tôi.
- **Bước tiếp theo:** đổi thứ tự ưu tiên thành `subject` → `container-title` → `type`. `container-title` có ở 15/24 item (kiểm tra bằng `crossref_response.json`), `type` có ở 24/24, nên độ phủ sẽ đạt 100% với ít nhất 2 nhóm giá trị phân biệt được.
- **Vì sao chưa áp dụng:** sửa trường này buộc phải parse lại raw records và chạy lại cả hai pipeline, làm đổi toàn bộ metrics. Chín file báo cáo của nhóm (`group_report.md`, 5 file `cp*.md`, 4 báo cáo cá nhân) đang trích số liệu hiện tại và sẽ lệch với artifact — đúng vào mục trừ điểm "báo cáo không match artifact thực tế". Đây là quyết định phải do cả nhóm chốt, không phải việc tôi tự sửa trước hạn nộp. Cách đo cải thiện nếu nhóm đồng ý làm: so `retrieval_hit_rate` riêng trên 6 sample loại `categories` trước và sau khi sửa.

## 7. Hiểu biết về luồng end-to-end

**1. Dữ liệu đi từ Crossref đến vector index như thế nào?**

`fetch_source_records` gọi `api.crossref.org/works` với `query` và `filter` lấy từ `Settings`, ghi payload nguyên trạng ra `crossref_response.json` **trước khi parse** — thứ tự này quan trọng, vì nếu parse lỗi thì vẫn còn nguồn để sửa parser mà không phải gọi lại API. `parse_crossref_payload` chuyển mỗi item thành `PaperRecord` với `paper_id` là DOI hạ chữ thường, ghi ra `crossref_records.json`. `build_clean_dataframe` chuẩn hoá và tính `age_days`, `text_for_embedding`; `validate_clean_dataframe` chặn nếu vi phạm contract. `LocalEmbeddingIndex.build` mã hoá `text_for_embedding` bằng MiniLM-L6-v2 và nạp vào collection `papers-baseline` với `paper_id` làm document ID — chính vì thế `paper_id` phải ổn định từ khâu ingestion.

**2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**

Mỗi sample có `question`, `ground_truth` và `ground_truth_doc_ids`. `retrieval_hit_rate` đo phần retrieval: top-k trả về có chứa `ground_truth_doc_ids` không — thuần tra ID, không phụ thuộc LLM. `mean_token_f1` và `judge_accuracy` đo phần sinh câu trả lời. Tách hai tầng như vậy để khi metric tụt còn biết lỗi nằm ở retrieval hay ở generation.

**3. Quality checks khác freshness monitoring ở điểm nào?**

Quality check hỏi "dữ liệu có đúng không" trên trạng thái hiện tại: ID trùng, summary rỗng, dòng trùng lặp. Freshness hỏi "dữ liệu có còn dùng được không" theo thời gian: `age_days` so với ngưỡng 180. Một dataset có thể đạt 11/11 quality mà vẫn quá hạn, và ngược lại. Ở corrupted, kịch bản `old_published_date` đẩy `max_age_days` từ 174 lên 851 — vượt ngưỡng, `is_fresh=false`. Trường hợp này quality check bắt được vì nhóm có thêm `freshness_age_days` trong bộ 11 check, nhưng bản chất hai tín hiệu vẫn khác nhau.

**4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**

Vì chỉ khi giữ nguyên đề bài thì chênh lệch metric mới quy được về dữ liệu. Đổi test set giữa chừng thì Δ phản ánh việc đổi câu hỏi, không phải tác động của corruption. Cùng lý do đó, `top_k` và evaluator cũng phải giữ nguyên — và snapshot raw cũng vậy, đó là phần tôi chịu trách nhiệm chứng minh.

**5. Repair được xem là thành công dựa trên artifact và metric nào?**

Ở mức tổng thể: 4 chỉ số chính về đúng baseline (Δ = 0), quality về 11/11, `is_fresh` về `true`. Nhưng Δ = 0 chưa loại trừ khả năng một bản ghi vẫn hỏng mà metric không đủ nhạy để thấy — với 24 sample, một sample sai chỉ làm metric đổi 4.2%. Vì vậy tôi bổ sung bằng chứng ở mức từng bản ghi trong `cp6_repair_lineage_proof.py`: 24/24 kiểm tra đạt, 5 trường quan trọng khớp 100% trên cả 24 dòng, và không dòng nào ở repaired thiếu DOI tương ứng trong raw response.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.000 | 0.667 | 1.000 | Tụt đúng bằng 8/24 sample. 2 bản ghi bị `drop_latest` × 4 loại câu hỏi = 8 — khớp chính xác, tức toàn bộ mức tụt đến từ việc mất document, không phải từ nhiễu embedding |
| `mean_token_f1` | 1.000 | 0.723 | 1.000 | Tụt ít hơn hit rate vì khi retrieve trượt, agent vẫn ghép được một phần chữ từ context sai |
| `judge_accuracy` | 1.000 | 0.708 | 1.000 | Bám sát hit rate — judge chấm sai chủ yếu ở đúng những câu mất document |
| `mean_judge_score` | 5 | 4 | 5 | Thang thô, chỉ đủ cho thấy xu hướng |
| Quality checks | 11/11 | 6/11 | 11/11 | 5 check đỏ: `paper_id_unique`, `duplicate_records`, `summary_not_null`, `summary_min_chars`, `freshness_age_days` |
| Freshness status | CÒN MỚI (0 dòng quá hạn, max 174 ngày) | QUÁ HẠN (1 dòng, max 851 ngày) | CÒN MỚI (0 dòng, max 174 ngày) | 851 = 174 + ~730 ngày bị đẩy lùi — khớp tham số trong corruption log |

### Kết luận từ số liệu

1. `drop_latest` xoá 2 bản ghi khỏi corpus → `duplicate_records` và `summary_not_null` báo đỏ, `freshness_age_days` bắt 1 dòng quá hạn, `is_fresh` chuyển `false` → `retrieval_hit_rate` tụt từ 1.000 xuống 0.667.
2. Chạy lại `build_clean_dataframe` từ `crossref_records.json` (sha256 chứng minh chưa từng bị đụng) → quality về 11/11, `is_fresh` về `true`, `max_age_days` về 174 → 4 chỉ số chính về đúng baseline, và 24/24 kiểm tra lineage ở mức bản ghi đều đạt.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**

`drop_latest`. Nó là kịch bản duy nhất làm document **biến mất khỏi corpus** — retrieval không thể trả về thứ không tồn tại, nên mức tụt 8/24 là mất trắng, không có cách nào chữa ở tầng agent. Bốn kịch bản còn lại chỉ làm nội dung xấu đi: bản ghi vẫn được retrieve, agent vẫn có context để bám. Xét từ vai trò của tôi, đây là lý do trực tiếp nhất để giữ raw snapshot bất biến — mất bản ghi ở tầng clean thì còn cứu được, mất ở tầng raw thì hết đường.

**Kết quả nào khác với kỳ vọng ban đầu?**

Tôi nghĩ `inject_noise` sẽ kéo metric xuống rõ, vì trực giác là chèn token rác vào summary sẽ làm lệch embedding. Thực tế nó gần như không đổi metric nào. Kiểm tra lại thì thấy lý do: marker chỉ dài 48 ký tự chèn vào summary trung bình 1727 ký tự, tỉ lệ quá nhỏ để dịch chuyển vector đủ xa; và câu hỏi trong test set chứa gần nguyên title nên retrieval gần như trùng khớp tuyệt đối, còn dư rất nhiều biên an toàn. Bài học là **chỉ số không đổi không chứng minh hệ thống bền** — nó chỉ nói kịch bản đó chưa đủ mạnh để chạm tới đường đi retrieval, một kết luận yếu hơn nhiều so với "hệ thống chịu được nhiễu".

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Lưu raw nguyên trạng trước khi parse là quyết định rẻ nhất mà đắt giá nhất của cả pipeline.** Nó không tốn gì lúc viết, nhưng chính vì có nó mà repair mới là "chạy lại từ nguồn" chứ không phải "vá tay kết quả", và toàn bộ phần chứng minh phục hồi của nhóm mới đứng vững.
2. **Bằng chứng phải phân biệt "không thể xảy ra" với "đã không xảy ra".** Đọc code để kết luận pipeline không fetch lại là suy luận; so sha256 trước và sau mới là bằng chứng. Tôi mất một vòng mới nhận ra ba mục kiểm tra đầu của mình đều thuộc loại thứ nhất.
3. **Định danh phải độc lập với dữ liệu có thể hỏng.** Chọn DOI thay vì hash title là quyết định trông nhỏ ở CP0, nhưng nó là lý do kịch bản `truncate_title` ở CP5 không làm mất dấu bản ghi.

### Nếu có thêm thời gian

Thêm kịch bản corrupt chính tầng raw — ví dụ xoá vài item trong `crossref_records.json` — rồi chạy lại repair. Toàn bộ kết luận "repair phục hồi 100%" của nhóm hiện dựa trên giả định raw còn nguyên; chưa ai kiểm chứng chuyện gì xảy ra khi giả định đó vỡ. Đo bằng cách so `retrieval_hit_rate` sau repair trong hai tình huống: raw nguyên vẹn (kỳ vọng 1.000, đã có) và raw bị hỏng (kỳ vọng thấp hơn, chưa có số). Nếu con số thứ hai cũng bằng 1.000 thì nghĩa là repair đang lấy dữ liệu từ chỗ khác chứ không phải từ raw — và như vậy cả kết luận hiện tại cũng cần xem lại.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng — tầng index ở CP2 báo `[SKIP]` và blocker `categories` ở §6 đều ghi đúng trạng thái chưa xong.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Thành Huy
**Ngày xác nhận:** 2026-08-07
