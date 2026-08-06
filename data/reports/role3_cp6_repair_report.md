# Vai trò 3 — CP6 Repair từ raw

- Baseline cleaning run date: `2026-08-06`
- Baseline rows: **24**
- Corrupted rows: **23**
- Repaired rows: **24**
- Repair status: **PASS**
- Quality: **11/11 checks pass**
- Freshness: **PASS**

## Baseline / corrupted / repaired

| Kiểm tra | Kết quả |
| --- | --- |
| `schema_matches_baseline` | PASS |
| `row_count_restored` | PASS |
| `paper_ids_restored` | PASS |
| `dropped_records_restored` | PASS |
| `missing_summary_restored` | PASS |
| `noise_removed` | PASS |
| `old_date_restored` | PASS |
| `duplicate_removed` | PASS |
| `repaired_ids_unique` | PASS |
| `repaired_embeddings_nonempty` | PASS |
| `corrupted_differs_from_baseline` | PASS |

Repaired dataset được tạo bằng cách nạp lại `data/raw/crossref_records.json` và gọi `build_clean_dataframe`; không copy hoặc sửa tay baseline/corrupted artifact.
