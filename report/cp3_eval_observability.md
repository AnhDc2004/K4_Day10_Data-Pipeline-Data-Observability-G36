# CP3 — Vai trò 5: Evaluation & Observability

> Checkpoint 3 · 01:35–02:00 · Nhóm 5 người
> Tiếp nối [cp2_eval_observability.md](cp2_eval_observability.md)
> Trạng thái: **baseline end-to-end đã chạy xong**, artifact và report khớp nhau.

---

## 1. Điều kiện tiền đề — B6 và B7 đã được vai trò 4 sửa

Chạy lại trước khi evaluate, tất cả xanh:

```
MANIFEST AUDIT     : success = True | 24 docs | collection = papers-baseline
  persist_portable : True          ← B6 đã sửa
  content drift    : [] / []        ← B7 đã sửa, index build lại từ clean mới
LocalEmbeddingIndex.load()          : OK, count = 24   ← trước đây crash
VERIFY test set vs index            : success = true, missing_doc_ids [], missing_titles []
```

Chỉ sau khi cả ba xanh tôi mới chạy evaluator — nếu không, metric sẽ phản ánh lệch phiên bản artifact chứ không phải chất lượng RAG.

---

## 2. Baseline metrics — `data/results/baseline_metrics.json`

| Metric | Giá trị |
| --- | --- |
| `samples` | 24 |
| `retrieval_hit_rate` | **1.000** |
| `mean_token_f1` | **1.000** |
| `judge_accuracy` | **1.000** |
| `mean_judge_score` | **5** |
| `ragas` | skipped (`RUN_RAGAS=1` mới chạy) |

Artifact kèm theo: `data/results/baseline_answers.json` (24 answer, 227 KB), `data/reports/phase1_report.md`.

**Judge là LLM thật, không phải fallback**: 0/24 answer có `"Fallback heuristic judge used"` trong `judge.reasoning`. Provider `openrouter`, model `openai/gpt-4o-mini`. Đây là điều kiện để được phép đọc `judge_accuracy` như một metric thật.

### Giải thích 3 nhóm metric

- **`retrieval_hit_rate`** — tỉ lệ câu hỏi mà *ít nhất một* trong top-4 document trả về có `paper_id` nằm trong `ground_truth_doc_ids`. Đây là metric của **tầng retrieval**, không quan tâm câu trả lời đúng hay sai.
- **`mean_token_f1`** — F1 trên **tập token** giữa `ground_truth` và `answer`, lowercase + chuẩn hoá khoảng trắng. Đo **tầng answer**, không cần LLM. Vì là tập hợp nên token lặp không được tính thêm.
- **`judge_accuracy` / `mean_judge_score`** — LLM chấm câu trả lời so với reference: `correct` (bool) và `score` 1–5. Bắt được trường hợp đúng nghĩa nhưng khác chữ, thứ mà token F1 bỏ sót.

---

## 3. Đọc một hit — và vì sao **không có miss nào**

### Một hit cụ thể

```
id             : 10.1111/exsy.70341::authors
question       : Who authored the paper 'Hi‐ RAG : A Hierarchical Retrieval‐Augmented Generation…'?
ground_truth   : Wei Tian, Yuhao Zhou
answer         : Wei Tian, Yuhao Zhou
gold doc ids   : ['10.1111/exsy.70341']
retrieved ids  : ['10.1111/exsy.70341', '10.63646/kpqm1958', '10.36227/…', '10.20944/…']
retrieval_hit  : True   token_f1: 1.0
judge          : score 5, correct=True — "matches the reference answer exactly"
```

Đường đi: câu hỏi chứa cụm `who authored` → `_extract_answer` lấy thẳng `metadata["authors_joined"]` của document ở rank 0; rank 0 chính là gold doc → answer trùng khít ground truth.

### Không có miss — và đó là điều phải nói thẳng

Kiểm tra toàn bộ 24 answer:

| Kiểm tra | Kết quả |
| --- | --- |
| `answer == ground_truth` (khớp chuỗi tuyệt đối) | **24/24** |
| gold doc ở rank 0 | 24/24 |
| `token_f1 < 1.0` | 0 sample |
| judge score | 5 ở cả 24 sample |
| số context mỗi câu | 4/4 (đúng `top_k`) |

**Baseline 1.000 là hệ quả của thiết kế, không phải bằng chứng hệ thống RAG mạnh.** Lý do có tính cấu trúc:

1. `_extract_answer` **không sinh văn bản** — nó trả về nguyên văn một trường metadata (`authors_joined`, `published`, `categories_joined`) hoặc câu đầu của `summary`.
2. Ground truth của tôi copy đúng trường đó từ cleaned dataframe.
3. Nên **hễ retrieval đặt đúng document ở rank 0 thì `token_f1` = 1.0 tất yếu**. Toàn bộ bài toán quy về retrieval.

Kiểm tra thêm: bỏ hẳn exact lookup, chỉ dùng semantic search thuần → gold vẫn ở rank 0 cho **24/24**. Corpus chỉ có 24 document và câu hỏi chứa nguyên title, nên embedding gần như trùng khớp. (Con số 0.83 ghi ở [CP2 §3b](cp2_eval_observability.md) là đo trên index và test set **trước khi rebuild**; sau rebuild là 1.00 — ghi lại để không nhầm.)

### Điều này có lợi gì cho CP5

Baseline kịch trần nghĩa là **mọi thay đổi sau corruption chỉ có thể đi xuống**, không có nhiễu nền. Ngược lại, phải cẩn thận khi diễn giải: một metric giảm sẽ nói lên tác động của corruption, nhưng metric giữ nguyên 1.0 **không** chứng minh hệ thống bền — chỉ nghĩa là corruption đó chưa chạm tới đường đi retrieval → metadata.

---

## 4. Đối chiếu report với artifact thật

`data/reports/phase1_report.md` được sinh từ chính payload JSON, không nhập tay. Đã kiểm từng con số:

| Mục trong report | Nguồn | Khớp |
| --- | --- | --- |
| 4 metric + samples | `baseline_metrics.json` | ✅ |
| 11 dòng quality check | `data/quality/baseline_quality.json` | ✅ |
| freshness (11 field) | `data/quality/freshness_report.json` | ✅ |
| `raw_records: 24` | `data/raw/crossref_records.json` | ✅ |
| `clean_rows: 24` | `data/clean/papers_clean.csv` | ✅ |
| `index_documents: 24`, collection | `data/embeddings/papers_embeddings.json` | ✅ |

**Sửa thêm:** report ban đầu in path tuyệt đối của máy (`I:\Day01-VinUni\…`). Rubric trừ điểm hard-code path và report sẽ được commit lên Git, nên `generate_phase1_report` nay rút gọn path về tương đối so với project root (`data\quality\baseline_quality.json`). Đã regenerate report từ artifact đã lưu — **không chạy lại evaluator**, nên không tốn thêm lần gọi LLM nào.

---

## 5. Baseline signals — mốc để đối chiếu sau giờ nghỉ

| Signal | Baseline |
| --- | ---: |
| `retrieval_hit_rate` | 1.000 |
| `mean_token_f1` | 1.000 |
| `judge_accuracy` | 1.000 |
| `mean_judge_score` | 5 |
| Quality checks | 11/11 PASS, `success: true` |
| `is_fresh` | true |
| `stale_rows` / `total_rows` | 0 / 24 |
| `latest_published` / `oldest_published` | 2026-08-01 / 2026-02-13 |
| `max_age_days` / `mean_age_days` | 174 / 76.4 |
| Index | `papers-baseline`, 24 document |
| Test set | 24 sample, 6 paper — **từ đây khoá cứng** |

Kể từ thời điểm này, test set **không được sinh lại nữa**: corrupted và repaired phải dùng đúng `data/eval/test_set.json` hiện tại, nếu không so sánh ba trạng thái mất công bằng.

---

## 5b. Bổ sung — probe set đo riêng tầng retrieval

Vấn đề ở §3: test set chính có title trong câu hỏi nên retrieval không thể sai, mọi metric kịch trần. Để có một thước đo **có biến thiên**, tôi thêm một test set phụ — `src/evaluation/retrieval_probe.py`:

- câu hỏi do LLM diễn đạt lại **từ abstract**, **cấm nhắc tới title** và cấm dấu nháy đơn (nháy đơn sẽ kích hoạt exact lookup);
- kiểm tự động: loại câu hỏi lặp ≥ 4 từ liên tiếp của title. Bộ lọc này thực sự hoạt động — **10/48 câu bị loại** (7 `repeats_title_ngram`, 3 `contains_single_quote`), tức LLM có lúc phớt lờ hướng dẫn;
- LLM chỉ được gọi **một lần duy nhất lúc sinh** (24 call), sau đó khoá vào file; lúc evaluate **không gọi LLM** vì chỉ đo retrieval.

**Đây là bộ đo phụ, KHÔNG thay thế `test_set.json` đã khoá** — baseline metrics ở §2 giữ nguyên, không phải chạy lại.

Artifact: `data/eval/test_set_retrieval_probe.json` (38 câu, phủ 23/24 paper), `data/eval/test_set_retrieval_probe_rejected.json`, `data/results/retrieval_probe_baseline.json`.

### Baseline probe — cuối cùng cũng có headroom

| Metric | Test set chính | **Probe set** |
| --- | ---: | ---: |
| `hit@4` | 1.000 | **0.868** |
| `top1` | 1.000 | **0.789** |
| `MRR` | — | **0.825** |

MRR nhạy hơn hit@4: khi corruption đẩy gold document từ rank 0 xuống rank 2, `hit@4` vẫn 1.0 nhưng MRR giảm — thấy được suy giảm mà hit rate che mất. Baseline đã có 3 trường hợp hit-nhưng-không-top1 (rank 1, rank 2).

### 5 miss nói lên điều gì — và một phát hiện về data

Soi từng miss thay vì chỉ ghi con số:

| Paper | Nguyên nhân |
| --- | --- |
| `10.47576/…` (2 probe) | Title/abstract **tiếng Nga**, câu hỏi tiếng Anh |
| `10.52060/juptik…` (2 probe) | Title/abstract **tiếng Indonesia** ("Chatbot Hybrid Fatwa MUI Menggunakan…") |
| `10.21203/rs.3.rs-9770645/v1` | Câu hỏi quá chung: "How was the QA corpus curated and formatted?" — hợp với nhiều paper |

**4/5 miss là do bất tương thích ngôn ngữ**: corpus đa ngữ nhưng `all-MiniLM-L6-v2` chỉ mạnh tiếng Anh, nên embedding của câu hỏi tiếng Anh không gần document tiếng Nga/Indonesia. Đây là một vấn đề data quality thật mà **không check nào hiện có bắt được**: paper tiếng Nga có `summary` dài, `published` hợp lệ, `text_for_embedding` không rỗng → qua sạch 11/11 check.

Đo thử bằng tỉ lệ ký tự ASCII: chỉ **1/24** paper bị phát hiện (paper tiếng Nga, ascii 0.60); paper tiếng Indonesia dùng bảng chữ Latin nên ascii = 1.00 và lọt lưới. Muốn bắt đủ thì cần language detection thật, không phải đếm ASCII — ghi lại như một hạn chế đã biết, không vá vội bằng heuristic sai.

### Dùng ở CP5/CP6 thế nào

Chạy `evaluate_retrieval` trên cùng probe set với ba index `papers-baseline` / `papers-corrupted` / `papers-repaired`, rồi đưa `hit@4`, `top1`, `MRR` vào bảng so sánh cạnh metric chính. Không tốn thêm lần gọi LLM nào.

---

## 6. Tự kiểm CP3

- [x] Chạy evaluator, tạo `baseline_answers.json` và `baseline_metrics.json`.
- [x] Đọc một hit chi tiết; xác nhận không có miss và giải thích được **vì sao** không có.
- [x] Kiểm ground truth và doc ID hợp lệ: 24/24 gold doc lookup được, `retrieval_hit` đúng.
- [x] Giải thích được `retrieval_hit_rate`, token F1 và judge metric.
- [x] Chạy data quality (11/11), freshness (`is_fresh: true`) và `generate_phase1_report`.
- [x] Đối chiếu report với JSON/CSV thật trước khi coi baseline hoàn tất.
- [x] Ghi baseline signals làm mốc sau nghỉ.
- [x] Xác minh judge không phải fallback heuristic (0/24).

### Ghi chú gửi vai trò 1 (integrator)

`script/run_phase1.py` / `src/pipelines/phase1.py` vẫn chưa implement. Tôi chạy baseline bằng script riêng gọi đúng các hàm đã có (`evaluate_pipeline` → `run_data_quality_checks` → `build_freshness_report` → `generate_phase1_report`). Khi vai trò 1 ráp `phase1.py`, thứ tự đó là thứ tự cần theo, và **phải audit manifest + verify test set trước khi evaluate** — đây là bước đã bắt được cả B6 lẫn B7.
