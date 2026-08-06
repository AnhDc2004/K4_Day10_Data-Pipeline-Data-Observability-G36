# CP5 + CP6 — Vai trò 5: Evaluation & Observability

> Checkpoint 5 (02:15–03:15) · Checkpoint 6 (03:15–04:00) · Nhóm 5 người
> Tiếp nối [cp3_eval_observability.md](cp3_eval_observability.md)
> Trạng thái: **corruption flow chạy end-to-end**, đủ artifact ba trạng thái, judge LLM thật ở cả ba.

Ghi chú: Số liệu trong file này thuộc lần chạy tại checkpoint. Số liệu cuối dùng cho bài nộp nằm ở data/results/*.json và group_report.md.
---

## 1. Phạm vi đã mở rộng
CP5/CP6 của tôi phụ thuộc corrupted/repaired dataset, mà `src/ingestion/corruption.py` (vai trò 3) và `src/pipelines/corruption_flow.py` (vai trò 1) chưa implement. Được nhóm đồng ý, tôi implement luôn cả hai để repo chạy được end-to-end:

| File | Nội dung |
| --- | --- |
| `src/ingestion/corruption.py` | 6 loại corruption, **deterministic** (chọn row theo vị trí ổn định, không random) |
| `src/pipelines/corruption_flow.py` | corrupt → rebuild index → evaluate → quality/freshness → repair từ raw → evaluate → comparison |
| `src/observability/reporting.py` | `generate_corruption_report` + phát hiện judge-fallback tự động |

Chạy: `uv run python script/run_corruption_flow.py`

---

## 2. Corruption đã làm gì — `data/results/corruption_log.json`

24 → 24 rows, **16 corruption**, mọi thứ đều log kèm before/after:

| Loại | Số row | Tác động dự kiến |
| --- | ---: | --- |
| `drop_latest_record` | 2 | mất hẳn document khỏi index |
| `blank_summary` | 3 | summary rỗng |
| `noise_summary` | 3 | chèn 76 ký tự noise hai đầu |
| `truncate_title` | 3 | giữ 15 ký tự đầu |
| `stale_published_date` | 3 | lùi 2000 ngày |
| `duplicate_row` | 2 | nhân bản nguyên row |

**Cảnh báo phương pháp luận:** corruption chọn row từ đầu dataframe, mà clean data sort theo `published` giảm dần, và test set cũng ưu tiên paper mới nhất → **cả 6/6 paper trong test set đều bị đụng**. Tác động vì thế là **cận trên**, không phải mức trung bình nếu corrupt ngẫu nhiên. Phải nói rõ khi trình bày, không được coi đây là ước lượng khách quan.

---

## 3. Kết quả ba trạng thái — `data/reports/corruption_report.md`

| Metric | Baseline | Corrupted | Repaired | Δ(corr−base) | Δ(rep−base) |
| --- | ---: | ---: | ---: | ---: | ---: |
| `retrieval_hit_rate` | 1.000 | 0.667 | 1.000 | **−0.333** | 0 |
| `mean_token_f1` | 1.000 | 0.671 | 1.000 | **−0.329** | 0 |
| `judge_accuracy` | 1.000 | 0.625 | 1.000 | **−0.375** | 0 |
| `mean_judge_score` | 5 | 3.708 | 5 | **−1.292** | 0 |

**Judge integrity: fallback 0/24 ở cả ba trạng thái** → `judge_accuracy` là LLM judge thật, so sánh được. (Xem §6 về lần chạy trước bị 403.)

### Probe set — tầng retrieval, không dùng exact lookup

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| `hit@4` | 0.868 | 0.763 | 0.868 |
| `top1` | 0.789 | 0.632 | 0.789 |
| `MRR` | 0.825 | 0.686 | 0.825 |

### Quality & freshness

| Trạng thái | Quality | Check fail | `is_fresh` | `stale_rows` | `max_age_days` |
| --- | --- | --- | --- | ---: | ---: |
| Baseline | 11/11 | — | true | 0 | 174 |
| Corrupted | **6/11** | `paper_id_unique`, `duplicate_records`, `summary_not_null`, `summary_min_chars`, `freshness_age_days` | **false** | 3 | 2067 |
| Repaired | 11/11 | — | true | 0 | 174 |

---

## 4. Chuỗi nhân quả — mỗi mắt xích có artifact

### 4.1 Drop record → mất document → hit rate sập

`corruption_log.json` ghi 2 record bị xoá (`10.1111/exsy.70341`, `10.2118/234689-pa`), cả hai đều nằm trong test set. Mỗi paper có 4 câu hỏi → **8/24 câu mất gold document**. Đúng bằng `retrieval_hit_rate = 16/24 = 0.667`. Toàn bộ mức giảm hit rate quy về đúng corruption này.

### 4.2 Blank/noise summary → answer sai nội dung

`token_f1` theo loại câu hỏi cho thấy tác động rất lệch nhau:

| Loại | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| `summary` | 1.00 | **0.18** | 1.00 |
| `authors` | 1.00 | 0.67 | 1.00 |
| `date` | 1.00 | 0.83 | 1.00 |
| `categories` | 1.00 | **1.00** | 1.00 |

Case cụ thể xấu đi nhất (`corrupted_answers.json`):

```
id      : 10.1111/exsy.70341::summary
GT      : "ABSTRACT As tool repositories for Large Language Model (LLM) agents grow…"
answer  : "Retrieval-Augmented Generation (RAG) has emerged as a powerful paradigm…"
hit     : False   token_f1: 0.194   judge: 2/5
```

Document gốc đã bị xoá khỏi index, nên retrieval trả về một paper khác cùng chủ đề RAG và agent tự tin trả lời bằng summary của paper sai. Đây chính là điều lab muốn chứng minh: **data hỏng không làm agent báo lỗi, nó làm agent trả lời sai một cách trôi chảy.**

### 4.3 Truncate title → không check nào bắt, nhưng retrieval vẫn xấu đi

Đúng như dự đoán ghi ở [CP0 §8](cp0_eval_observability_contract.md): `truncate_title` **không làm fail bất kỳ check nào** trong 11 check (`title_not_null` vẫn pass vì title chỉ ngắn đi, không rỗng). Nhưng probe MRR giảm 0.825 → 0.686 và top1 giảm 0.789 → 0.632, một phần đến từ 3 title bị cắt.

Đây là bằng chứng cho luận điểm xuyên suốt: **quality check pass không có nghĩa data sạch, nếu check không nhìn đúng chỗ.**

### 4.4 `categories` — metric đẹp nhưng vô nghĩa

`categories` giữ nguyên `token_f1 = 1.00` ở corrupted **dù hit_rate chỉ 0.67**. Nghĩa là: với 8 câu mà retrieval trả về **sai paper**, answer vẫn trùng khít ground truth.

Lý do đã cảnh báo từ [CP1 B4](cp1_eval_observability.md): Crossref không trả field `subject` nên **cả 24 paper đều có `categories_joined = "Uncategorized"`**. Trả lời sai paper vẫn ra đúng chữ.

Kết luận phải nói thẳng: **loại câu hỏi `categories` không mang tín hiệu nào** và nó kéo `mean_token_f1` lên cao giả tạo. Nếu bỏ loại này, mức sụt của corrupted sẽ sâu hơn con số 0.671.

---

## 5. CP6 — Repair và đánh giá phục hồi

Repair chạy lại cleaning **từ `data/raw/crossref_records.json`**, không sửa tay corrupted data:

```python
raw_records = load_raw_records(settings.paths.raw_records_json)
repaired_df = build_clean_dataframe(raw_records, now_utc())
```

**Kết quả: phục hồi hoàn toàn trên mọi metric** — cả 4 metric chính, cả 3 probe metric, quality 11/11, `is_fresh` true, `max_age_days` về 174. Δ(repaired − baseline) = 0 ở tất cả.

Điều này **kỳ vọng được**, không phải may mắn: raw snapshot còn nguyên và cleaning là hàm thuần, nên clean lại từ raw phải ra đúng dataset ban đầu. Nếu Δ ≠ 0 thì đó mới là dấu hiệu cleaning không deterministic.

Giới hạn phải nêu: repair thành công **vì raw còn nguyên**. Nếu corruption xảy ra ở tầng raw hoặc ở chính nguồn Crossref thì không có điểm khôi phục nào — kịch bản này chưa được kiểm chứng trong lab.

---

## 6. Ba lỗi bắt được trong lúc chạy CP5/CP6

### B8 — `phase1.py` ghi đè baseline bằng số liệu sai (vai trò 1 + vai trò 3)

Nghiêm trọng nhất. Baseline `mean_token_f1` bị ghi thành **0.750** thay vì 1.000. Nguyên nhân: 6 câu `date` có `token_f1 = 0`:

```
ground_truth : '2026-08-01 00:00:00+00:00'   ← test set build từ CSV
answer       : '2026-08-01T00:00:00+00:00'   ← index build từ dataframe in-memory (Timestamp)
```

Gốc rễ là **B3 nêu từ CP1 chưa ai sửa**: `published` không được chuẩn hoá thành chuỗi. Cùng một dữ liệu nhưng đi qua CSV thì ra dấu cách, giữ in-memory thì ra `T` — và metric tụt vì **định dạng**, không phải vì chất lượng data.

Đã xử lý: rebuild baseline index từ CSV-read dataframe → baseline về 1.000; `corruption_flow` cũng đọc lại repaired từ CSV trước khi evaluate.

**Sửa triệt để (đề nghị vai trò 3):** cleaning ghi `published` dạng chuỗi `YYYY-MM-DD` trong chính dataframe. Khi đó CSV và in-memory giống hệt nhau và cả lớp lỗi này biến mất.

### B9 — Judge im lặng rơi về heuristic khi OpenRouter trả 403

Lần chạy đầu, API trả 403 giữa chừng: corrupted 14/24 rồi 24/24, repaired 24/24 dùng heuristic — nhưng `judge_accuracy` vẫn ra số đẹp như thường. Đúng cái bẫy ghi ở [CP0 §1.4](cp0_eval_observability_contract.md).

Đã xử lý: thêm `_judge_integrity()` vào flow và bảng "Độ tin cậy của judge metric" vào comparison report, kèm cảnh báo tự động khi có fallback. Sau khi API hoạt động lại, chạy lại → **0/24 fallback ở cả ba trạng thái**, cảnh báo tự tắt.

### B10 — Repo kẹt giữa merge chưa resolve

`data/quality/freshness_report.json` còn nguyên conflict marker `<<<<<<< HEAD` (JSON hỏng, flow crash ngay bước 1) và `data/chroma/chroma.sqlite3` ở trạng thái unmerged. Đã resolve: bỏ track `chroma.sqlite3` theo đúng ý `.gitignore` mới, regenerate `freshness_report.json`. **Chưa commit** — để nhóm quyết.

---

## 7. Tự kiểm CP5 + CP6

- [x] Corruption có chủ đích, deterministic, log đầy đủ record ID / type / parameter / before-after.
- [x] Corrupted dùng path và collection riêng; baseline **không bị ghi đè** bởi flow.
- [x] Evaluate corrupted bằng **đúng test set đã khoá**, không sinh lại.
- [x] Tìm được case xấu đi có evidence (`10.1111/exsy.70341::summary`, f1 0.194, judge 2/5).
- [x] Kiểm evaluator không silently fallback — và đã bắt được đúng lúc nó fallback thật.
- [x] Quality/freshness cho corrupted lưu file riêng, không đè baseline.
- [x] Nối corruption log ↔ quality signal ↔ metric change bằng số liệu thật.
- [x] Ghi rõ signal **không đổi** (`truncate_title` không fail check nào; `categories` giữ f1 = 1.00) để tránh kết luận quá mức.
- [x] Repair từ raw, evaluate lại, tính delta ba trạng thái.
- [x] Comparison report sinh từ metrics/quality/freshness thật, path tương đối, không hard-code số.
- [x] Nêu giới hạn: test set 24 sample, corruption đụng 6/6 paper test set, repair chỉ thành công vì raw còn nguyên.

### Việc còn lại của nhóm

1. **Sửa B8 tận gốc** — cleaning chuẩn hoá `published` thành chuỗi, rồi chạy lại `phase1.py`. Không sửa thì bất kỳ ai chạy `phase1.py` cũng sẽ ghi đè baseline bằng `mean_token_f1 = 0.750`.
2. **Commit merge đang treo** (§B10) sau khi review.
3. `data/quality/` hiện có **hai** file baseline quality: `baseline_quality.json` (của tôi) và `phase1-baseline_quality.json` (do `phase1.py` đặt tên khác) — nên thống nhất một tên.
