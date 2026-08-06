# Phase 1 - Baseline Report

Generated at: 2026-08-06T16:21:10.334383+00:00

## 1. Source & scope

| Field | Value |
| --- | --- |
| `source_api` | Crossref REST API |
| `source_query` | agentic retrieval augmented generation large language model |
| `source_filter` | from-pub-date:2026-02-07,has-abstract:true |
| `max_results` | 24 |
| `raw_records` | 24 |
| `clean_rows` | 24 |
| `index_collection` | papers-baseline |
| `index_documents` | 24 |
| `embedding_model` | sentence-transformers/all-MiniLM-L6-v2 |
| `llm_provider` | openrouter |
| `llm_model` | openai/gpt-4o-mini |
| `top_k` | 4 |
| `test_set_samples` | 24 |

## 2. Evaluation metrics

| Field | Value |
| --- | --- |
| `So sample` | 24 |
| `Retrieval hit rate` | 1.000 |
| `Mean token F1` | 1.000 |
| `Judge accuracy` | 1.000 |
| `Mean judge score` | 5 |

> Ragas: skipped - Set RUN_RAGAS=1 to enable the slower Ragas pass.

## 3. Data quality

- Ket qua tong: **PASS** (11/11 check pass)
- Total rows: 24
- Report: `data\quality\baseline_quality.json`

| Check | Ket qua | Observed | Expected | Chi tiet |
| --- | --- | --- | --- | --- |
| `row_count_min` | PASS | 24 | >= 10 rows |  |
| `schema_columns_present` | PASS | 8 | 8 cot bat buoc |  |
| `paper_id_not_null` | PASS | 0 | 0 missing |  |
| `paper_id_unique` | PASS | 24 | 24 unique |  |
| `duplicate_records` | PASS | 0 | 0 duplicate rows |  |
| `title_not_null` | PASS | 0 | 0 missing |  |
| `summary_not_null` | PASS | 0 | 0 missing |  |
| `text_for_embedding_not_empty` | PASS | 0 | 0 missing |  |
| `summary_min_chars` | PASS | 0 | 0 row < 100 ky tu |  |
| `published_parseable` | PASS | 0 | 0 row khong parse duoc ngay |  |
| `freshness_age_days` | PASS | 174 | max age_days <= 180, 0 row thieu age_days |  |

## 4. Freshness

| Field | Value |
| --- | --- |
| `latest_published` | 2026-08-01 |
| `oldest_published` | 2026-02-13 |
| `stale_rows` | 0 |
| `total_rows` | 24 |
| `is_fresh` | true |
| `freshness_threshold_days` | 180 |
| `max_age_days` | 174 |
| `min_age_days` | 5 |
| `mean_age_days` | 76.400 |
| `missing_published` | 0 |
| `generated_at` | 2026-08-06T16:21:09.798379+00:00 |
| `report_path` | data\quality\freshness_report.json |

## 5. Evidence & limitations

- Metrics doc tu artifact JSON do evaluator ghi ra; report nay khong tinh lai so lieu.
- Kiem tra `judge.reasoning` trong answers: neu la fallback heuristic thi `judge_accuracy` khong phai LLM judge.
- Test set duoc khoa va dung lai nguyen ven cho corrupted/repaired.
