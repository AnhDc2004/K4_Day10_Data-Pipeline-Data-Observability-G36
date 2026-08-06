# CP2 — Vai trò 5: Evaluation & Observability

> Checkpoint 2 · 01:05–01:35 · Nhóm 5 người
> Tiếp nối [cp1_eval_observability.md](cp1_eval_observability.md)
> Trạng thái: **test set đã khoá (24 sample)**, quality/freshness baseline đã ghi, khuôn phase-1 report đã chạy được. Còn chờ vai trò 4 build index để verify doc ID.

---

## 1. Đã implement

| File | Hàm | Nội dung |
| --- | --- | --- |
| `src/evaluation/testset.py` | `build_test_set(df, output_path)` | select → draft → **validate** → `write_json` |
| `src/evaluation/testset.py` | `validate_test_set(test_set, df)` | kiểm 5 key, id trùng, question/ground_truth rỗng, doc_id có thật trong clean |
| `src/evaluation/testset.py` | `verify_test_set_against_index(test_set, index)` | mọi `paper_id` **và** title trong câu hỏi phải `index.lookup()` ra được |
| `src/observability/quality.py` | `audit_index_manifest(settings, manifest_path, df)` | audit collection name, embedding model, document count, đối chiếu paper_id với clean |
| `src/observability/reporting.py` | `generate_phase1_report(...)` | render markdown 5 mục từ payload thật, không hard-code số |

`build_test_set` **raise thay vì hạ tiêu chuẩn**: nếu chọn được < 6 paper hợp lệ thì dừng kèm lý do loại, vì test set quá nhỏ làm mọi kết luận về corruption ở CP5 mất giá trị.

---

## 2. Test set đã khoá — `data/eval/test_set.json`

**24 sample = 6 paper × 4 loại** (summary / authors / date / categories), 10.727 bytes.

| paper_id | Title |
| --- | --- |
| `10.2118/234689-pa` | SafeRAG: A Large-Language-Model-Based Multistage Retrieval-Augmented… |
| `10.1007/s10278-026-02086-9` | JADE-Plus: A Multimodal Agentic Retrieval-Augmented Generation LLM… |
| `10.21203/rs.3.rs-10178277/v1` | Retrieval-Augmented Large-Language-Model-Based Time-Series Forecasting… |
| `10.2196/preprints.106157` | Does retrieval-augmented generation impact medical students' perceptio… |
| `10.3390/buildings16132637` | An Agentic AI System for Roof Design Compliance Using Computer Vision… |
| `10.21079/11681/50309` | Microsoft Azure artificial intelligence / machine learning hackathon… |

Đọc lại **từ file** (không dùng biến trong memory) để xác minh:

- 24 sample, mỗi loại đúng 6;
- key đúng contract `metrics.evaluate_pipeline`: `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`;
- 6 paper riêng biệt, không có `ground_truth` rỗng, không có id trùng;
- 0 câu hỏi còn markup.

Ví dụ một sample:

```
id                   : 10.3390/buildings16132637::date
question_type        : date
question             : When was the paper 'An Agentic AI System for Roof Design Compliance
                       Using Computer Vision, Retrieval-Augmented Generation and Large
                       Language Models' published?
ground_truth         : 2026-07-02 00:00:00+00:00
ground_truth_doc_ids : ["10.3390/buildings16132637"]
```

### Một quyết định: loại paper có markup trong title

Khi draft lần đầu, paper `10.1111/exsy.70341` lọt vào test set với title chứa **markup JATS thô**:

```
Hi‐ <scp>RAG</scp> : A Hierarchical Retrieval‐Augmented Generation Framework…
```

Đo mức độ trên toàn dataset: **1/24 title** có tag (`<scp>`, `</scp>`) và ký tự `U+2010`; **summary sạch 0/24**.

Cân nhắc hai phương án:

1. **Strip markup ngay trong test set** — sai, vì `_extract_answer` trả về nguyên văn `metadata` của index. Nếu ground truth bị strip mà index vẫn giữ markup thì hai bên lệch nhau và `token_f1` tụt vì lỗi của tôi, không phải vì data.
2. **Loại paper đó khỏi test set** (đã chọn) — thêm luật `title_contains_markup` vào `paper_rejection_reason`. Dataset có 24 row nên vẫn dư paper để chọn đủ 6, và câu hỏi giữ được sạch.

Vẫn gửi vai trò 3 như một cải thiện (không block): cleaning nên strip tag JATS và chuẩn hoá `U+2010` về `-` trong `title`/`summary`. Nếu sửa, **phải rebuild cả index lẫn test set** để hai bên không lệch.

---

## 3. Audit embedding manifest — đã chạy sau commit `role4_cp2`

`audit_index_manifest(settings, embeddings_json, df)` → **success = False**, nhưng chỉ vì đúng **một** vấn đề; toàn bộ phần nội dung đều đạt:

| Hạng mục | Kết quả |
| --- | --- |
| `collection_name` | `papers-baseline` ✅ |
| `embedding_model` | `sentence-transformers/all-MiniLM-L6-v2`, khớp `settings` ✅ |
| `document_count` / `unique_paper_ids` | 24 / 24 — không có document trùng ✅ |
| Đối chiếu với clean (24 rows) | `missing_from_index: []`, `extra_in_index: []` ✅ |
| **`persist_path_portable`** | ❌ **FAIL** |

### B6 — Manifest ghi `persist_path` tuyệt đối của máy build (gửi vai trò 4)

```
manifest persist_path : W:\AI\K4_Day10_Data-Pipeline-Data-Observability-G36\data\chroma
máy này  chroma_dir   : I:\Day01-VinUni\...\K4_Day10_...\data\chroma
```

Hậu quả đã kiểm chứng bằng cách gọi thật:

```
LocalEmbeddingIndex.load(settings, paths.embeddings_json)
→ LOAD FAIL: InternalError: failed to create whole tree
```

`index.py:138` đọc `Path(payload["persist_path"])` từ manifest thay vì dùng `settings.paths.chroma_dir`, nên **index không load được trên bất kỳ máy nào khác máy đã build** — CP3 chạy `phase1.py` sẽ chết ở đây. Rubric cũng trừ điểm mục "hard-code path".

Đề nghị sửa (1 dòng, thuộc quyền vai trò 4): `load()` dùng `settings.paths.chroma_dir` thay cho `payload["persist_path"]`, hoặc manifest ghi path tương đối so với project root.

Bản thân dữ liệu Chroma **có được commit và đọc được tại chỗ**: `data/chroma/` chứa collection `papers-baseline` với đúng 24 document.

Tôi đã thêm check `persist_path_portable` vào `audit_index_manifest` để lỗi loại này không lọt qua im lặng nữa.

---

## 3b. Verify test set ↔ index — **PASS 100%**

Chạy `verify_test_set_against_index` (dựng index bằng `chroma_dir` cục bộ để đi vòng B6):

```
samples          : 24
unique_doc_ids   : 6
missing_doc_ids  : []      ← mọi paper_id lookup được
missing_titles   : []      ← mọi title trong câu hỏi lookup được
success          : true
```

Đây là điều kiện cuối trước evaluate, và nó đã đạt.

### Preview retrieval (chỉ search, **không gọi LLM**, không ghi artifact)

| Cấu hình | hit_rate@4 | top1 |
| --- | ---: | ---: |
| `answer_question` đầy đủ (có exact lookup) | **1.00** | **1.00** |
| Semantic search thuần (bỏ exact lookup) | 1.00 | 0.83 |

Hai điều rút ra cho CP3/CP5:

1. **Baseline `retrieval_hit_rate` gần như chắc chắn = 1.00** → mọi thay đổi ở CP5 chỉ có thể đi xuống, tức là corruption sẽ hiện rõ trên metric này.
2. **Exact lookup đang gánh phần lớn kết quả** (top1 1.00 → 0.83 khi bỏ đi). Nên `retrieval_hit_rate` đo khả năng lookup theo title nhiều hơn là chất lượng semantic search. Điều này củng cố dự đoán ở [CP0 §8](cp0_eval_observability_contract.md): corruption **truncate title** sẽ đánh mạnh nhất, dù không check quality nào bắt được nó.

---

## 4. Baseline signals để đối chiếu sau corruption

Đã ghi lại (số liệu ở [cp1_eval_observability.md §7](cp1_eval_observability.md)):

| Artifact | Signal |
| --- | --- |
| `data/quality/baseline_quality.json` | 11/11 check PASS, `success: true`, 24 rows |
| `data/quality/freshness_report.json` | `is_fresh: true`, `stale_rows 0/24`, latest `2026-08-01`, max_age `174` |
| `data/eval/test_set.json` | 24 sample — **khoá cứng**, dùng lại nguyên vẹn cho corrupted và repaired |

---

## 5. Khuôn phase-1 report

`generate_phase1_report` render 5 mục: Source & scope → Evaluation metrics → Data quality (bảng từng check) → Freshness → Evidence & limitations. Đã smoke-test renderer bằng số liệu giả **ghi vào thư mục tạm, không đụng `data/`** → 67 dòng markdown. CP3 chỉ cần truyền metrics thật vào.

Mục "Evidence & limitations" tự nhắc kiểm `judge.reasoning` để phát hiện fallback heuristic.

---

## 5b. Sau commit `cp2 - 3` (cleaning strip markup) — test set phải build lại

### Unit test của nhóm: 8/8 PASS

```
python -m unittest discover -s tests -v   →  Ran 8 tests ... OK
```

`tests/test_cleaning.py` (vai trò 3, 6 test) và `tests/test_retrieval_contract.py` (vai trò 4, 2 test) là **contract regression test**: mỗi người khoá lời hứa của module mình thành assert, để lần sau sửa code mà làm vỡ contract thì test đỏ ngay thay vì phát hiện qua metric tụt. Không phải test set evaluation của tôi. (`pytest` chưa cài trong `.venv`, chạy bằng `unittest` là đủ.)

Đáng chú ý: `test_html_entities_and_jats_markup_are_removed_before_embedding` — vai trò 3 đã làm đúng đề nghị ở §2, giờ strip cả tag JATS lẫn HTML entity.

### Hệ quả: 3 artifact lệch nhau

Cleaning mới decode `&amp;` → `&`, `&lt;` → `<`, và bỏ `<scp>`. Ba nguồn đang ở hai phiên bản khác nhau:

| Artifact | Build từ clean lúc | Tình trạng |
| --- | --- | --- |
| `data/clean/papers_clean.csv` | commit `cp2 - 3` (mới nhất) | ✅ nguồn chuẩn |
| `data/embeddings/` + `data/chroma/` | commit `role4_cp2` (cũ) | ❌ lệch 1 title, 3 `text_for_embedding` |
| `data/eval/test_set.json` (bản đầu) | clean cũ | ❌ 1/24 ground_truth còn `&amp;` |

Ví dụ lệch cụ thể:

```
index  : "Title: Hi‐ <scp>RAG</scp> : A Hierarchical…"      clean: "Title: Hi‐ RAG : A Hierarchical…"
index  : "( Q = 25.66, p &lt; 0.001)"                        clean: "( Q = 25.66, p < 0.001)"
index  : "research and development (R&amp;D) mission"        clean: "research and development (R&D) mission"
```

### Đã làm: rebuild test set từ clean mới

Baseline metrics **chưa hề được tính**, nên rebuild bây giờ không vi phạm nguyên tắc khoá test set — khoá chỉ có hiệu lực từ baseline trở đi. Kết quả:

- 24 sample, 6 paper, 4 loại × 6 — quality vẫn **11/11 PASS**, freshness `is_fresh: true`;
- **0 paper bị loại** (trước là 1 vì markup);
- `10.1111/exsy.70341` nay hợp lệ và vào test set, thay cho `10.21079/11681/50309`.

### B7 — Index phải rebuild từ clean hiện tại (vai trò 4)

`audit_index_manifest` (đã thêm check drift nội dung) bắt được:

```
content_drift_title: ['10.1111/exsy.70341']
content_drift_text : ['10.1111/exsy.70341', '10.1007/s10278-026-02086-9', '10.21079/11681/50309']
```

Và `verify_test_set_against_index` **nay FAIL đúng chỗ đó**:

```
missing_titles: ["Hi‐ RAG : A Hierarchical Retrieval‐Augmented Generation Framework…"]
success: false
```

Index vẫn giữ title bản `<scp>` nên exact lookup theo title mới trượt. Nếu evaluate ở trạng thái này, sample của paper đó mất boost lookup và `token_f1` giảm **vì artifact lệch phiên bản, không phải vì chất lượng RAG**.

Cần: vai trò 4 rebuild index từ `papers_clean.csv` hiện tại (kèm sửa B6). Sau đó tôi chạy lại `audit_index_manifest` + `verify_test_set_against_index`, cả hai phải `success: true` trước khi CP3 evaluate.

**Nguyên tắc rút ra:** clean data, index và test set phải được sinh từ **cùng một snapshot**. Bất kỳ ai chạy lại cleaning thì index và test set đều phải build lại theo.

---

## 6. Tự kiểm CP2

- [x] `build_test_set` có đủ `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`.
- [x] Question tạo từ cleaned data, ground truth copy nguyên văn cột nguồn.
- [x] Test set lưu cố định tại `data/eval/test_set.json` và đã đọc thử lại từ file.
- [x] Baseline quality/freshness signals đã ghi để đối chiếu sau corruption.
- [x] Khuôn phase-1 report chạy được, chỉ chờ số liệu thật ở CP3.
- [x] Audit embedding manifest: collection name, embedding model, document count đều audit được — 24/24 khớp clean.
- [x] Verify doc ID trong index: 6/6 paper_id và 6/6 title lookup được, `success: true`.
- [x] Unit test của nhóm: 8/8 PASS (`python -m unittest discover -s tests`).
- [x] Test set build lại từ clean mới sau khi cleaning strip markup — 24 sample, 0 paper bị loại.
- [x] **B6 đã xử lý bởi vai trò 4**: manifest ghi `data\\chroma` dạng tương đối; `LocalEmbeddingIndex.load()` dùng `settings.paths.chroma_dir` của checkout hiện tại.
- [x] **B7 đã xử lý bởi vai trò 4**: index được rebuild từ clean snapshot hiện tại; manifest không còn title markup `<scp>` và verify trả `success: true`.
