# Phase 1 - Baseline Report

Generated at: 2026-08-06T18:36:38.291894+00:00

## 1. Source & scope

| Field | Value |
| --- | --- |
| `source` | Crossref REST API |
| `query` | agentic retrieval augmented generation large language model |
| `raw_records` | 24 |
| `clean_records` | 24 |
| `freshness_threshold_days` | 180 |

## 2. Evaluation metrics

| Field | Value |
| --- | --- |
| `So sample` | 24 |
| `Retrieval hit rate` | 0.833 |
| `Mean token F1` | 0.676 |
| `Judge accuracy` | 0.875 |
| `Mean judge score` | 4.583 |

| Field | Value |
| --- | --- |
| `total_samples` | 24 |
| `answer_relevancy` | 0.171 |
| `answer_relevancy_n` | 24 |
| `context_precision` | 0.667 |
| `context_precision_n` | 24 |
| `context_recall` | 0.708 |
| `context_recall_n` | 24 |
| `faithfulness` | 0.618 |
| `faithfulness_n` | 24 |

## 3. Data quality

- Ket qua tong: **PASS** (11/11 check pass)
- Total rows: 24
- Report: `E:\Lab1\K4_Day10_Data-Pipeline-Data-Observability-G36\data\quality\phase1-baseline_quality.json`

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
| `freshness_age_days` | PASS | 175 | max age_days <= 180, 0 row thieu age_days |  |

## 4. Freshness

| Field | Value |
| --- | --- |
| `latest_published` | 2026-08-01 |
| `oldest_published` | 2026-02-13 |
| `stale_rows` | 0 |
| `total_rows` | 24 |
| `is_fresh` | true |
| `freshness_threshold_days` | 180 |
| `max_age_days` | 175 |
| `min_age_days` | 6 |
| `mean_age_days` | 83.800 |
| `missing_published` | 0 |
| `generated_at` | 2026-08-06T18:34:47.753560+00:00 |
| `report_path` | E:\Lab1\K4_Day10_Data-Pipeline-Data-Observability-G36\data\quality\freshness_report.json |

## 5. Evidence & limitations

- Metrics doc tu artifact JSON do evaluator ghi ra; report nay khong tinh lai so lieu.
- Kiem tra `judge.reasoning` trong answers: neu la fallback heuristic thi `judge_accuracy` khong phai LLM judge.
- Test set duoc khoa va dung lai nguyen ven cho corrupted/repaired.
