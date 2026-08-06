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

## 3. Audit embedding manifest — **đang bị block**

```
MANIFEST AUDIT: success = False
Chua co embedding manifest -- index chua duoc build.
```

`data/embeddings/` và `data/chroma/` đều trống. `audit_index_manifest` đã sẵn sàng, khi vai trò 4 build xong sẽ kiểm:

- `collection_name` = `papers-baseline`;
- `embedding_model` khớp `settings.embedding_model` (`all-MiniLM-L6-v2`);
- `document_count` = 24 và không có `paper_id` trùng;
- không có paper_id nào có trong clean mà thiếu trong index (và ngược lại).

Chỉ sau bước này mới chạy được `verify_test_set_against_index` — đó là điều kiện cuối trước khi evaluate ở CP3.

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

## 6. Tự kiểm CP2

- [x] `build_test_set` có đủ `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`.
- [x] Question tạo từ cleaned data, ground truth copy nguyên văn cột nguồn.
- [x] Test set lưu cố định tại `data/eval/test_set.json` và đã đọc thử lại từ file.
- [x] Baseline quality/freshness signals đã ghi để đối chiếu sau corruption.
- [x] Khuôn phase-1 report chạy được, chỉ chờ số liệu thật ở CP3.
- [ ] **Blocked (vai trò 4)**: chưa audit được embedding manifest và chưa verify được doc ID trong index — `data/embeddings/` và `data/chroma/` còn trống.
