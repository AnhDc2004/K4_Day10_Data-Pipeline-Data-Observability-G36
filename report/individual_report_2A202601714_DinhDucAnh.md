# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Đinh Đức Anh |
| MSSV | 2A202601714 |
| Khóa/Lớp | K4 |
| Tên nhóm | G36 |
| Vai trò chính | Role 1 — Pipeline integrator (kiêm nhóm trưởng) |
| Repository | https://github.com/AnhDc2004/K4_Day10_Data-Pipeline-Data-Observability-G36 |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

Phạm vi theo bảng phân công nhóm 5 người: `src/core/` · `src/pipelines/` — settings, orchestration, release.

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Settings & path contract | `src/core/config.py` — `Settings`, `Paths` | `.env`, tham số lab | Cấu hình dùng chung cho cả 5 vai trò: `source_query`, `source_filter`, `max_results=24`, `top_k=4`, `freshness_threshold_days=180`, 3 collection name, `refresh_source` / `refresh_test_set` | Hoàn thành |
| Tiện ích I/O dùng chung | `src/core/utils.py` — `read_json`, `write_json`, `normalize_whitespace` | — | Hàm I/O thống nhất, `write_json` tự tạo thư mục cha | Hoàn thành |
| Orchestration baseline | `src/pipelines/phase1.py`, `script/run_phase1.py` | Raw snapshot, clean data, index của VT2–VT4 | Chạy 8 bước end-to-end → `baseline_metrics.json`, `baseline_answers.json`, `data/quality/*`, `data/reports/phase1_report.md` | Hoàn thành |
| Orchestration corruption flow | `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py` | Clean data + raw snapshot | `corrupted_*` / `repaired_*` metrics, answers, quality, `corruption_report.md` | Hoàn thành — *xem ghi chú bàn giao bên dưới* |
| Release & checklist cuối | Toàn repo | Artifact của cả nhóm | Kiểm no-secret, no-hard-code-path, report khớp artifact | Một phần — còn 3 mục mở (§9) |

> **Ghi chú bàn giao cần thống nhất với VT5:** `cp5_cp6_eval_observability.md` §1 ghi rằng tại thời điểm CP5, `src/pipelines/corruption_flow.py` chưa được implement và VT5 đã viết giúp để repo chạy được end-to-end. Trước khi nộp, hai bên cần chốt lại ai là người viết bản cuối cùng đang có trong repo và sửa dòng tương ứng ở bảng trên — không nhận ownership cho phần mình không trực tiếp viết.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Debug lỗi Ragas nuốt exception | VT5 — `src/evaluation/metrics.py` | Tìm ra `KeyError(0)` do `dict(result)` không tương thích ragas ≥ 0.2; vá bằng `_summarize_ragas`; 4 chỉ số Ragas nay có trong cả 3 file metrics (§6) |
| Loại trừ nghi vấn embeddings sai | VT4 — `src/retrieval/embeddings.py` | Viết script đối chứng: cosine(cùng câu) = 1.0000, cosine(khác câu) = −0.0270 → `MiniLMEmbeddings` đối xứng và sạch, loại bỏ giả thuyết sai trước khi đi tiếp |
| Truy vết chênh lệch metric giữa báo cáo CP và artifact | VT5 — các file `cp*_eval_observability.md` | Phát hiện CP3/CP5 ghi baseline = 1.000 còn artifact cuối ghi 0.8333 — số liệu của hai lần chạy khác nhau, đã đưa thành cảnh báo trong báo cáo nhóm §12 |
| Chuẩn hoá `published` thành chuỗi `YYYY-MM-DD` | VT3 — `src/ingestion/cleaning.py` | Truy ra lỗi `token_f1 = 0` của 6 câu `date` là do CSV và index metadata ghi ngày hai định dạng khác nhau; sửa một dòng trong `build_clean_dataframe` → `mean_token_f1` từ 0.6756 lên 1.0000 mà không đụng gì tới RAG |
| Thống nhất ngôn ngữ và bổ sung nội dung hai report | VT5 — `src/observability/reporting.py` | Gộp nhãn hiển thị vào 4 dict dùng chung cho cả hai hàm, chuyển toàn bộ sang tiếng Việt có dấu; thêm hai cột Δ, bảng so sánh Ragas và mục "Mức phục hồi" theo đúng CP0 §7.2; ghi file bằng UTF-8 tường minh để không lỗi encoding trên Windows |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Chốt contract cấu hình cho 5 vai trò | `src/core/config.py` | Mọi module đọc cùng một nguồn tham số; không ai hard-code `top_k`, ngưỡng freshness hay tên collection | VT5 trích dẫn trực tiếp `config.py:63`, `:64,73`, `:127-129`, `:133` trong contract CP0 |
| Orchestrate baseline 8 bước | `script/run_phase1.py` | Chạy hết không lỗi, sinh đủ artifact | Log 8/8 step; `data/reports/phase1_report.md` sinh 2026-08-06T18:36 UTC |
| Tách path/collection cho 3 trạng thái | `Paths`, `corruption_flow.py` | `papers-baseline` / `papers-corrupted` / `papers-repaired` riêng biệt; baseline không bị ghi đè | `baseline_metrics.json` và `repaired_metrics.json` cùng tồn tại, giá trị khác nhau đúng như thiết kế |
| Điều phối repair từ nguồn đáng tin | `corruption_flow.py` | Repair chạy lại `build_clean_dataframe` từ `data/raw/crossref_records.json`, không sửa tay | 24/24 answer của repaired trùng khít baseline đến từng ký tự |
| Sửa lỗi Ragas chặn 4 chỉ số | `src/evaluation/metrics.py` | `baseline/corrupted/repaired_metrics.json` đều có `answer_relevancy`, `context_precision`, `context_recall`, `faithfulness` kèm `_n` | So file trước/sau: `"error": "Ragas evaluation failed: 0"` → 4 chỉ số + `total_samples: 24` |
| Siết bước verify test set ↔ index thành điều kiện chặn | `src/pipelines/phase1.py` | Baseline không còn bị đo trên artifact lệch phiên bản | Log Step 6: `Cảnh báo lệch match` → `Verify Test Set vs Index thành công! Tổng số câu hỏi: 24` |
| Bổ sung agent demo artifact | `script/run_agent_demo.py`, `data/results/agent_demo_answers.json` | 4 câu hỏi chạy qua agent có tool, gồm một câu ngoài corpus để kiểm chứng agent không bịa | Mở file: câu hỏi quantum cryptography được trả lời là không có trong corpus |
| Chạy checklist release CP6: report khớp artifact, không hard-code path | `src/observability/reporting.py`, `src/pipelines/corruption_flow.py` | Cột Baseline của hai dòng observability nay đọc từ `data/quality/` thay vì hard-code `PASSED`/`FRESH`; đường dẫn trong report rút về tương đối | So `corruption_report.md` trước/sau: cột Baseline đổi từ chuỗi cố định sang `11/11 → 6/11 → 11/11` |

**Một output cụ thể phần việc của tôi tạo ra:**

`data/results/baseline_metrics.json` trước khi tôi sửa chỉ có `{"ragas": {"error": "Ragas evaluation failed: 0"}}`. Sau khi vá, file chứa đủ 4 chỉ số Ragas kèm trường `{metric}_n` — và chính trường `_n` này sau đó phát hiện thêm một vấn đề mà không ai để ý: `corrupted_metrics.json` có `faithfulness_n = 23` trong khi baseline và repaired có 24. Nghĩa là corrupted có một mẫu NaN bị loại khỏi mẫu số, nên con số 0.558 đang được làm đẹp; nếu tính NaN = 0 trên đủ 24 mẫu thì giá trị thật là **0.535**. So 0.558 với 0.729 là so hai thứ khác cơ sở.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Năm người viết năm module độc lập, mỗi người chạy trên máy khác nhau với path khác nhau. Vai trò của tôi là làm cho năm mảnh đó ghép lại chạy được như một pipeline, và quan trọng hơn: **chạy lại được** trên máy bất kỳ, ra đúng số cũ. Nếu không có một nguồn cấu hình duy nhất và một thứ tự thực thi cố định thì baseline không tái lập được, và toàn bộ so sánh ba trạng thái mất ý nghĩa.

### Cách triển khai

**Settings là nguồn sự thật duy nhất.** `Settings` là dataclass với toàn bộ tham số bắt buộc, không có default ẩn. Điều này gây bất tiện khi viết script rời — gọi `Settings()` trực tiếp sẽ báo thiếu 23 tham số — nhưng đó là ý đồ: không ai được vô tình chạy pipeline với cấu hình mặc định khác cấu hình của nhóm. Mọi module đọc `top_k`, ngưỡng freshness, tên collection từ đây thay vì tự đặt số.

**Thứ tự 8 bước có ràng buộc, không phải danh sách tuần tự.** `run_phase1.py` chạy: settings → raw → cleaning + validate retrieval contract → build index → quality/freshness → test set + verify → evaluate → report. Ba điểm chặn quan trọng: validate clean schema **trước** khi build index; verify test set ↔ index **trước** khi evaluate; report đọc lại từ file JSON đã ghi chứ không nhận số từ biến trong bộ nhớ. Điểm thứ ba nghe thừa nhưng nó chính là thứ đảm bảo report không thể "đẹp hơn" artifact.

**Ba trạng thái, ba đường dẫn.** `Paths` cấp path riêng cho clean data, embeddings và results của baseline / corrupted / repaired. Quy tắc "không ghi đè baseline" của lab chỉ thực thi được ở tầng cấu hình — nếu để module tự đặt tên file thì sớm muộn cũng có người ghi đè.

**Repair là hàm thuần chạy lại từ raw.** Không có nhánh "sửa" nào trong corruption flow đọc corrupted data. Nó nạp raw snapshot và gọi lại đúng `build_clean_dataframe` mà baseline đã dùng.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `.env` (provider, API key), raw snapshot `data/raw/crossref_records.json`, clean dataframe của VT3, index của VT4 |
| Output | `Settings` cho mọi module; artifact 3 trạng thái trong `data/results/`, `data/quality/`, `data/reports/` |
| Module phụ thuộc | `ingestion/crossref.py` (VT2), `ingestion/cleaning.py` + `corruption.py` (VT3), `retrieval/index.py` (VT4), `evaluation/metrics.py` + `observability/*` (VT5) |
| Module sử dụng output | Tất cả — mọi vai trò đều import `Settings` và ghi vào path do `Paths` cấp |
| Điều kiện lỗi cần xử lý | Raw snapshot thiếu → load lại thay vì fetch mới (giữ baseline ổn định); clean schema fail contract → dừng trước khi build index; test set lệch index → **hiện chỉ cảnh báo, chưa dừng** (§6) |

### Cách xác minh

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** cả hai chạy hết, sinh đủ artifact 3 trạng thái, baseline không bị ghi đè, report khớp JSON.
- **Kết quả thực tế:** đạt. `run_phase1.py` chạy 8/8 step; `baseline_metrics.json` và `repaired_metrics.json` cùng tồn tại với giá trị đúng; `phase1_report.md` và `corruption_report.md` khớp số trong JSON.
- **Artifact/log:** `data/reports/phase1_report.md`, `data/reports/corruption_report.md`, `data/results/*.json`. Log đã che secret; không có API key trong output.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Sau khi tìm ra nguyên nhân lỗi Ragas là code viết cho ragas 0.1.x còn `.venv` cài ragas ≥ 0.2, phải chọn cách khắc phục cho cả nhóm.

- **Các phương án đã cân nhắc:**
  1. **Pin `ragas==0.1.x`** trong dependency — code giữ nguyên, không phải sửa gì.
  2. **Viết hàm đọc kết quả tương thích cả hai phiên bản** — thêm `_summarize_ragas(result)` đọc `result.scores` và tự tính trung bình.

- **Phương án đã chọn:** phương án 2.

- **Lý do:** phương án 1 rẻ hơn nhưng đẩy rủi ro sang người khác. Bốn thành viên còn lại đang có `.venv` riêng; ai đã cài ragas 0.2 sẽ phải gỡ và cài lại, và bất kỳ ai `uv sync` sau này trên môi trường mới cũng có thể lệch. Với vai trò integrator, tiêu chí là **repo chạy được trên máy bất kỳ** chứ không phải trên máy tôi. Phương án 2 tốn thêm khoảng 20 dòng nhưng làm code sống với cả hai phiên bản. Tôi cũng tận dụng luôn để thêm trường `{metric}_n` — thứ mà bản `dict(result)` cũ không bao giờ có.

- **Bằng chứng quyết định phù hợp:** cả ba file metrics đều có đủ 4 chỉ số Ragas sau khi sửa. Và trường `_n` phát sinh từ quyết định này đã bắt được lỗi mẫu số lệch ở corrupted (`faithfulness_n = 23`) — một vấn đề mà nếu pin version thì sẽ không bao giờ lộ ra.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**

  ```json
  "ragas": { "error": "Ragas evaluation failed: 0" }
  ```

  Trong khi log lại cho thấy `Evaluating: 100%|██████| 96/96 [01:21<00:00]` và pipeline in `PIPELINE PHASE 1 ĐÃ CHẠY HOÀN THÀNH THÀNH CÔNG!`.

- **Lệnh hoặc bước tái hiện:**

  ```powershell
  $env:RUN_RAGAS="1"
  python script/run_phase1.py
  # rồi mở data/results/baseline_metrics.json, xem trường "ragas"
  ```

- **Nguyên nhân gốc:** `_run_ragas` kết thúc bằng `return dict(result)`. Code viết theo API ragas 0.1.x, nơi `evaluate()` trả về `Result` kế thừa `dict`. Từ ragas 0.2, hàm trả về `EvaluationResult` không có `keys()`, nên `dict()` lùi về giao thức tuần tự kiểu cũ và gọi `result[0]`; `__getitem__` tra `_scores_dict[0]` trong khi dict đó chỉ có key là tên metric → `KeyError: 0`. Exception bị `except Exception` bắt và chuyển thành chuỗi, nên **không xuất hiện trong log** và pipeline chạy tiếp bình thường. Nói cách khác: 96 phép đánh giá và khoảng 400 lần gọi LLM đã chạy xong, rồi bị vứt đi ở đúng dòng cuối cùng.

  Chuỗi `"0"` cũng là manh mối: nó không phải thông báo lỗi mà là toàn bộ nội dung của exception — dấu hiệu của `KeyError(0)` chứ không phải lỗi mạng hay thiếu cột (những lỗi đó đều có message mô tả).

- **Cách xử lý:** ba thay đổi trong `_run_ragas`:
  1. `f"...{exc}"` → `f"...{exc!r}"` và ghi kèm `traceback.format_exc()`;
  2. `return dict(result)` → `return _summarize_ragas(result)`, hàm mới đọc `result.scores` và tự tính trung bình, tương thích cả hai phiên bản;
  3. thêm `{metric}_n` — số mẫu thực sự chấm được sau khi lọc NaN.

  Thay đổi (1) là thứ phá được thế bí: nó biến thông báo vô nghĩa `0` thành `KeyError(0)` kèm số dòng và stack trỏ thẳng vào `ragas/dataset_schema.py:460`.

- **Cách xác minh sau khi sửa:** chạy lại với `RUN_RAGAS=1` → trường `ragas` có `total_samples: 24` và đủ 4 chỉ số kèm `_n`.

- **Điều học được:** `except Exception` nuốt traceback biến một lỗi một dòng thành nhiều giờ mò mẫm — bắt exception thì phải giữ lại `repr` và stack, nếu không thì thà để nó nổ. Và một pipeline in "THÀNH CÔNG" không chứng minh mọi bước bên trong đều thành công; phải mở artifact ra đọc, không tin log.

### Blocker thứ hai (đã xử lý) — baseline bị nhiễm bởi hai lỗi đo lường

Sau khi Ragas chạy được, baseline vẫn chỉ đạt `retrieval_hit_rate` 0.8333 và `mean_token_f1` 0.6756 — thấp hơn hẳn dự đoán ở CP2. Soi từng câu trong `baseline_answers.json` tách ra hai nguyên nhân độc lập, **cả hai đều là lỗi đo lường, không phải chất lượng RAG**.

**Nguyên nhân 1 — test set lệch index.** Cả 4 câu miss đều thuộc **một** paper duy nhất, `10.1111/exsy.70341`, trùng khớp với cảnh báo ở Step 6 của log:

```
Cảnh báo lệch match giữa Test Set và Index:
{'samples': 24, 'missing_doc_ids': ['10.1111/exsy.70341'], 'success': False}
```

`phase1.py` chỉ `logger.warning` rồi chạy tiếp, nên artifact lệch phiên bản vẫn được đem đi đo. Đã sửa: rebuild index và test set từ cùng một clean snapshot, và siết bước verify thành điều kiện chặn thay vì cảnh báo — đúng nguyên tắc đã áp dụng cho `validate_clean_dataframe` ngay phía trên.

**Nguyên nhân 2 — `published` không được chuẩn hoá thành chuỗi.** Cả 6 câu loại `date` có `token_f1 = 0`, nhưng 5/6 câu được LLM judge chấm **5/5**:

```
ground_truth : 2026-07-02 00:00:00+00:00     ← test set đọc từ CSV
answer       : 2026-07-02T00:00:00+00:00     ← index metadata qua .isoformat()
```

`cleaning.py` để `published` ở dạng `Timestamp`, rồi hai đường ghi tách ra: CSV cho dấu cách, còn `index.py::_metadata_value` gọi `.isoformat()` cho chữ `T`. Tập token không giao nhau nên F1 bằng 0 dù nội dung đúng tuyệt đối. Đã sửa bằng một dòng trong `build_clean_dataframe`:

```python
df["published"] = df["published"].dt.strftime("%Y-%m-%d")
```

- **Cách xác minh sau khi sửa:** chạy lại `run_phase1.py`. Log Step 6 in `Verify Test Set vs Index thành công! Tổng số câu hỏi: 24`, và `baseline_metrics.json` cho `retrieval_hit_rate = 1.0`, `mean_token_f1 = 1.0` — giá trị 1.0 **chằn** xác nhận cả 6 câu `date` nay khớp tuyệt đối.

- **Điều học được:** clean data, index và test set bị ràng buộc chặt với nhau; chỉ cần một người chạy lại cleaning mà không rebuild hai cái kia là metric tụt vì lệch phiên bản chứ không vì chất lượng. Và một metric tụt chưa chắc là hệ thống kém — phải soi phân bố theo nhóm trước khi kết luận, vì hai lỗi định dạng đã che mất một baseline hoàn hảo.

**Lỗi này tái phát ở nhánh corrupted và phải sửa lần hai.** Sau khi baseline về 1.000, `mean_token_f1` của corrupted vẫn chỉ 0.5565. Soi `corrupted_answers.json` thấy đúng dấu hiệu cũ: 4 câu `date` có `hit = True`, judge chấm 5/5, nhưng F1 = 0. Nguyên nhân nằm ở `corruption.py` — nó gọi `pd.to_datetime` để lùi ngày cho kịch bản `old_published_date`, biến `published` từ chuỗi ngược về `Timestamp` và không chuyển lại. Baseline và repaired đều đi qua `build_clean_dataframe` nên có `strftime`, riêng nhánh corrupted thì không. Đã thêm bước chuẩn hoá vào `_rebuild_derived_fields`; `mean_token_f1` corrupted lên **0.7231**, tức báo cáo trước đó đang phóng đại thiệt hại do corruption thêm 0.167.

Bài học bổ sung: sửa một lỗi ở một nhánh không có nghĩa nhánh song song đã sạch. Ba trạng thái baseline/corrupted/repaired đi qua ba đường ghi dữ liệu khác nhau, nên mọi thay đổi về định dạng phải kiểm cả ba.

## 7. Hiểu biết về luồng end-to-end

**1. Dữ liệu đi từ Crossref đến vector index như thế nào?**
`crossref.py` gọi REST API với `query` và `filter` lấy từ `Settings`, lưu **nguyên văn response trước khi parse** rồi mới parse thành `PaperRecord` với `paper_id` = DOI. `cleaning.py` chuẩn hoá title/summary/authors/categories, parse `published`, pad partial date, tính `age_days`, ghép `text_for_embedding`, ghi ra `papers_clean.csv`. `index.py` embed `text_for_embedding` bằng MiniLM-L6-v2 rồi nạp vào Chroma collection `papers-baseline`, kèm metadata scalar (Chroma không nhận list nên authors/categories phải là `*_joined` dạng string). Việc giữ raw response nguyên vẹn chính là thứ làm repair khả thi ở CP6.

**2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
Mỗi sample có 5 field. `ground_truth_doc_ids = [paper_id]` copy trực tiếp từ clean dataframe, không tự sinh. Khi evaluate, `answer_question` trả về `retrieved_doc_ids`; `retrieval_hit` = có giao với `ground_truth_doc_ids` hay không → đo **tầng retrieval**. Còn `ground_truth` (chuỗi) đem so với `answer` bằng token F1 và bằng LLM judge → đo **tầng answer**. Tách hai tầng như vậy cho phép nói được corruption làm hỏng ở đâu: mất document, hay lấy đúng document nhưng trả lời sai.

**3. Quality checks khác freshness monitoring ở điểm nào?**
Quality check hỏi "dữ liệu có đúng hình dạng không" — đủ row, ID unique, không trùng, không rỗng, summary đủ dài. Freshness hỏi "dữ liệu có còn mới không" — `age_days` so với ngưỡng 180. Một dataset có thể sạch tuyệt đối mà vẫn cũ mèm, và ngược lại. Bài lab chứng minh điều đó: corruption `stale_published_date` đẩy `is_fresh` sang false mà không làm fail check nào về hình dạng; còn `truncate_title` thì không tín hiệu nào bắt được cả hai.

**4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
Vì metric chỉ so sánh được khi mẫu số giống hệt nhau. Nếu sinh lại test set sau corruption, `build_test_set` sẽ tự loại các paper đã hỏng và chọn paper khác — corrupted khi đó được chấm trên bộ đề dễ hơn, và Δ đo được sẽ phản ánh việc đổi đề chứ không phải tác động của data hỏng. Khoá test set là điều kiện để phép so sánh trung thực.

**5. Repair được xem là thành công dựa trên artifact và metric nào?**
Ba tầng bằng chứng, không chỉ một con số. (a) **Metric**: cả 4 chỉ số chính của repaired bằng baseline đến chữ số cuối — `0.8333333333333334`, `0.6756410256410257`, `0.875`, `4.583333333333333`. (b) **Signal**: quality về 11/11 PASS, `is_fresh` về true. (c) **Answer**: so từng câu giữa `repaired_answers.json` và `baseline_answers.json` cho **0/24 câu khác nhau** — trùng khít từng ký tự. Tầng (c) mới là bằng chứng repair thật chứ không phải vá metric: nếu chỉ chỉnh số thì các câu trả lời không thể giống hệt nhau như vậy.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | --: | --: | --: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.6667 | 1.0000 | 24/24 → 16/24 → 24/24. Toàn bộ mức giảm quy về đúng 8 câu của 2 paper bị `drop_latest` |
| `mean_token_f1` | 1.0000 | 0.7231 | 1.0000 | Bị loại `categories` (luôn = 1.0) kéo lên cao giả tạo; xem phân tích theo loại ở báo cáo nhóm §10 |
| `judge_accuracy` | 1.0000 | 0.7083 | 1.0000 | 24/24 → 17/24 → 24/24. Judge là LLM thật ở cả ba (0/24 fallback) |
| `mean_judge_score` | 5 | 4.0000 | 5 | Giảm đúng 1.00 điểm trên thang 5 |
| Quality checks | 11/11 PASS | 6/11 PASS | 11/11 PASS | 5 check fail đúng như thiết kế corruption |
| Freshness status | FRESH | STALE | FRESH | `stale_rows` 0 → 1 → 0 |

### Kết luận từ số liệu

**1. `drop_latest` xoá 2 record khỏi clean data → `row_count_min` fail, quality xuống 6/11 → hit rate 24/24 xuống 16/24 và judge accuracy 1.000 xuống 0.7083.**

`corruption_log.json` ghi thao tác này với `{"count": 2, "sort_field": "published", "order": "descending"}` kèm hai `record_ids`. Mỗi paper trong test set có 4 câu hỏi nên 2 paper bị xoá = 8 câu mất gold document. Số học khớp chính xác: `(24 − 8)/24 = 0.6667`.

**2. Repair chạy lại cleaning từ `data/raw/crossref_records.json` → quality về 11/11 PASS và `is_fresh` về true → cả 4 chỉ số chính về đúng baseline, Δ = 0.**

Mức phục hồi 100% này là kỳ vọng được chứ không phải may mắn: raw snapshot còn nguyên và cleaning là hàm thuần, nên clean lại từ raw bắt buộc phải ra đúng dataset ban đầu. Nếu Δ ≠ 0 thì mới là dấu hiệu cleaning không deterministic — và đó chính là thứ phép thử này kiểm chứng.

### Corruption nào ảnh hưởng rõ nhất và vì sao?

`drop_latest`, vì nó tác động ở tầng thấp nhất. Các corruption khác làm dữ liệu **xấu đi** — summary rỗng, title cụt, ngày sai — nhưng document vẫn còn trong index nên retrieval vẫn có cơ hội tìm thấy. Drop thì lấy đi hẳn thứ để tìm; không kỹ thuật retrieval nào cứu được. Một record bị xoá kéo theo cả 4 câu hỏi của paper đó, tức 16.7% test set cho mỗi record.

Điều đáng nói hơn con số nằm ở nội dung câu trả lời: agent **không hề báo lỗi** khi document biến mất. Nó lấy một paper khác cùng chủ đề RAG rồi trả lời trôi chảy bằng metadata của paper sai. Đây là bài học chính của lab — data hỏng không làm agent crash, nó làm agent trả lời sai một cách tự tin.

### Kết quả nào khác với kỳ vọng ban đầu?

**Vòng chạy đầu, baseline chỉ đạt 0.8333 và 0.6756 thay vì 1.000 như CP2 dự đoán.** Giả thuyết đầu tiên là retrieval yếu. Đã bác bỏ bằng cách soi từng câu: 4 câu miss đều thuộc một paper duy nhất, và 6 câu `date` có F1 = 0 nhưng judge lại chấm 5/5 — hai dấu hiệu không thể đến từ chất lượng RAG. Truy tiếp ra hai lỗi đo lường độc lập, đã sửa cả hai (§6), baseline về đúng 1.000.

**Bất ngờ thứ hai: `answer_relevancy` của Ragas chỉ 0.184 trong khi judge accuracy là 1.000.** Đọc `per_sample` thì 6 mẫu bị điểm 0 **đúng là 6 câu loại `categories`** — ragas gắn cờ "noncommittal" cho câu trả lời `"Uncategorized"`, và cờ đó hoàn toàn hợp lý. Tương tự, `context_precision` bằng 0 rơi đúng vào 6 câu `date`, vì answer là chuỗi ngày trần không thể hiện việc dùng context. Hai chỉ số này đang đo đặc điểm thiết kế của ground truth chứ không đo hệ thống — đã ghi vào giới hạn thay vì dùng làm bằng chứng.

**Bất ngờ thứ ba, từ agent demo.** Câu "What is the newest paper in the corpus about?" được trả lời **sai**: agent chỉ ra paper `published = 2026-07-10` trong khi `freshness_report.json` ghi `latest_published: 2026-08-01`. Nguyên nhân có tính cấu trúc — bộ tool chỉ có `semantic_search_papers` và `lookup_paper`, không tool nào sắp xếp theo ngày, nên agent suy đoán từ kết quả semantic search. Đáng chú ý là cùng hệ thống đó, khi hỏi về quantum cryptography (chủ đề ngoài corpus) lại trả lời đúng "không có". Ranh giới mà agent tự nhận ra được là ranh giới **nội dung**, không phải ranh giới **khả năng của tool**.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

**1. Về data pipeline — clean data, index và test set phải sinh từ cùng một snapshot.**
Ba artifact này trông độc lập nhưng bị ràng buộc chặt: chỉ cần một người chạy lại cleaning mà không rebuild hai cái kia là metric tụt vì lệch phiên bản chứ không vì chất lượng. Baseline 0.8333 ở vòng chạy đầu là cái giá của đúng lỗi đó. Với vai trò integrator, bài học cụ thể là kiểm tra nhất quán artifact phải là **điều kiện chặn** trong orchestration, không phải một dòng cảnh báo rồi chạy tiếp — và tôi đã sửa `phase1.py` đúng theo hướng đó.

**2. Về data quality/observability — check pass không có nghĩa data sạch, nếu check không nhìn đúng chỗ.**
`truncate_title` không làm fail bất kỳ check nào trong 11 check, vì `title_not_null` chỉ hỏi title có rỗng không chứ không hỏi nó có còn nguyên không. Ngược lại, một metric đẹp cũng không có nghĩa hệ thống tốt: loại `categories` giữ F1 = 1.000 ngay cả khi retrieval sai paper, vì mọi paper đều có ground truth `"Uncategorized"`. Quan sát được hay không phụ thuộc vào việc có ai đặt đúng câu hỏi hay không.

Bản thân report cũng dính đúng bẫy này: mục "Mức phục hồi" tự sinh ban đầu chỉ quét 4 chỉ số chính nên kết luận "mọi chỉ số đều Δ = 0", trong khi bảng ngay phía trên cho thấy `faithfulness` lệch +0.042. Một mục tóm tắt tự sinh mà không đọc hết dữ liệu của chính nó thì nguy hiểm hơn là không có, vì nó tạo cảm giác đã được kiểm chứng.

**3. Về ảnh hưởng của data đến RAG agent — hỏng dữ liệu không gây lỗi, nó gây câu trả lời sai trôi chảy.**
Không có exception nào, không có dòng log đỏ nào khi document bị xoá. Agent lấy paper gần nhất còn lại và trả lời như thật. Nếu chỉ nhìn log hoặc exit code thì corruption hoàn toàn vô hình — chỉ có evaluation set với ground truth mới phát hiện được. Agent demo cho thấy cùng một điểm ở dạng khác: agent tự nhận ra được ranh giới nội dung ("không có paper nào về quantum cryptography") nhưng không nhận ra ranh giới khả năng của chính bộ tool mình có.

### Nếu có thêm thời gian

Chạy probe set (`retrieval_probe.py`) trên cả ba collection và đưa `hit@4`, `top1`, `MRR` vào bảng so sánh cạnh bốn chỉ số chính.

Lý do chọn việc này: baseline hiện đạt 1.000 tuyệt đối, nhưng đó là **kịch trần do thiết kế** chứ không phải bằng chứng RAG mạnh — câu hỏi chứa nguyên title nên `answer_question` bắt được bằng exact lookup, và `_extract_answer` trả nguyên văn metadata mà ground truth copy từ chính cột đó. Một thước đo kịch trần thì không phân biệt được hệ thống tốt với hệ thống vừa đủ. Probe set bỏ title ra khỏi câu hỏi, buộc semantic search phải làm việc thật, nên có biến thiên để đo.

Cách đo cải thiện: probe set chạy **không tốn lần gọi LLM nào** lúc evaluate vì chỉ đo retrieval. Kỳ vọng `hit@4` baseline nằm dưới 1.000 — và quan trọng hơn, `MRR` sẽ bắt được thứ mà `hit@4` che mất: khi corruption đẩy gold document từ rank 0 xuống rank 2, hit rate vẫn 1.0 nhưng MRR giảm.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đinh Đức Anh
**Ngày xác nhận:** 2026-08-06
