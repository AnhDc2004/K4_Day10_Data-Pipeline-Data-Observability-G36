# Corruption Impact Report

Generated at: 2026-08-06T16:44:41.671296+00:00

## 1. Metric ba trang thai

| Metric | Baseline | Corrupted | Repaired | d(corrupted-baseline) | d(repaired-baseline) |
| --- | ---: | ---: | ---: | ---: | ---: |
| `retrieval_hit_rate` | 1.000 | 0.667 | 1.000 | -0.333 | 0 |
| `mean_token_f1` | 1.000 | 0.671 | 1.000 | -0.329 | 0 |
| `judge_accuracy` | 1.000 | 0.625 | 1.000 | -0.375 | 0 |
| `mean_judge_score` | 5 | 3.708 | 5 | -1.292 | 0 |

So sample: baseline 24 / corrupted 24 / repaired 24 (phai bang nhau -- cung mot test set da khoa).

### Do tin cay cua judge metric

| Trang thai | Judge LLM that | Fallback heuristic |
| --- | ---: | ---: |
| baseline | 24/24 | 0/24 |
| corrupted | 24/24 | 0/24 |
| repaired | 24/24 | 0/24 |

### Probe set (do rieng tang retrieval, khong dung exact lookup)

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| `top1_accuracy` | 0.789 | 0.632 | 0.789 |
| `mrr` | 0.825 | 0.686 | 0.825 |
| `retrieval_hit_rate_at_4` | 0.868 | 0.763 | 0.868 |

## 2. Data quality signals

| Trang thai | Ket qua | Rows | Check fail |
| --- | --- | ---: | --- |
| Baseline | 11/11 pass | 24 | - |
| Corrupted | 6/11 pass | 24 | `paper_id_unique`, `duplicate_records`, `summary_not_null`, `summary_min_chars`, `freshness_age_days` |
| Repaired | 11/11 pass | 24 | - |

## 3. Freshness

| Trang thai | is_fresh | stale_rows | latest_published | max_age_days |
| --- | --- | ---: | --- | ---: |
| Baseline | true | 0 | 2026-08-01 | 174 |
| Corrupted | false | 3 | 2026-07-13 | 2067 |
| Repaired | true | 0 | 2026-08-01 | 174 |

## 4. Corruption log

| type | paper_id | parameter | before | after |
| --- | --- | --- | --- | --- |
| drop_latest_record | 10.1111/exsy.70341 | top-N moi nhat | 2026-08-01 00:00:00+00:00 | <removed> |
| drop_latest_record | 10.2118/234689-pa | top-N moi nhat | 2026-08-01 00:00:00+00:00 | <removed> |
| blank_summary | 10.1007/s10278-026-02086-9 | summary -> chuoi rong | 1869 chars | 0 chars |
| blank_summary | 10.21203/rs.3.rs-10178277/v1 | summary -> chuoi rong | 1945 chars | 0 chars |
| blank_summary | 10.2196/preprints.106157 | summary -> chuoi rong | 1765 chars | 0 chars |
| noise_summary | 10.3390/buildings16132637 | chen 76 ky tu noise moi dau | 2207 chars | 2361 chars |
| noise_summary | 10.21079/11681/50309 | chen 76 ky tu noise moi dau | 826 chars | 980 chars |
| noise_summary | 10.63646/kpqm1958 | chen 76 ky tu noise moi dau | 1635 chars | 1789 chars |
| truncate_title | 10.21203/rs.3.rs-10012178/v1 | giu 15 ky tu dau | Retrieval-Augmented Generation (RAG), Generative AI, and Age... | Retrieval-Augme |
| truncate_title | 10.47576/2949-1894.2026.7.7.023 | giu 15 ky tu dau | Снижение рисков применения LLM (Large Language Model) в сфер... | Снижение рисков |
| truncate_title | 10.21203/rs.3.rs-9882260/v1 | giu 15 ky tu dau | Operationalizing Reliability Gaps in Large Language Models: ... | Operationalizin |
| stale_published_date | 10.52060/juptik.v4i1.4318 | -2000 ngay | 2026-06-01 00:00:00+00:00 (age 66) | 2020-12-09 00:00:00+00:00 (age 2066) |
| stale_published_date | 10.54254/2753-8818/2026.dl34055 | -2000 ngay | 2026-06-01 00:00:00+00:00 (age 66) | 2020-12-09 00:00:00+00:00 (age 2066) |
| stale_published_date | 10.22214/ijraset.2026.82233 | -2000 ngay | 2026-05-31 00:00:00+00:00 (age 67) | 2020-12-08 00:00:00+00:00 (age 2067) |
| duplicate_row | 10.1007/s10278-026-02086-9 | nhan ban nguyen row | 1 row | 2 rows |
| duplicate_row | 10.21203/rs.3.rs-10178277/v1 | nhan ban nguyen row | 1 row | 2 rows |

## 5. Doc ket qua

**Recovery**: hoan toan -- moi metric repaired bang baseline.

**Signal khong doi sau corruption**: khong co -- moi metric deu thay doi.

**Gioi han cua ket luan**:

- Test set chi co 24 sample, moi sample sai lam metric doi dang ke; khong suy rong ra ngoai corpus nay.
- Metric o bang 1 duoc tinh boi evaluator tren cung mot test set da khoa cho ca ba trang thai.
- Kiem `judge.reasoning` trong answers: neu la fallback heuristic thi `judge_accuracy` khong phai LLM judge.
