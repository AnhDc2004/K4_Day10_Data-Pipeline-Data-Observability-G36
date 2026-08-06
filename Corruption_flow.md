┌───────────────────────────────────────────────────────────────┐
  │ 1. CORRUPT (Tạo dữ liệu lỗi cố ý từ Baseline Data)          │
  │    Input:  data/clean/papers_clean.csv (Baseline)           │
  │    Output: data/clean/papers_clean_corrupted.csv            │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼ Handoff: Corrupted Clean DataFrame
  ┌─────────────────────────────────────────────────────────────────────┐
  │ 2. REBUILD (Xây dựng Index riêng cho Corrupted Dataset)             │
  │    Collection Name: "papers-corrupted"                              │
  │    Manifest Output: data/embeddings/papers_embeddings_corrupted.json│
  └──────────────────────────────┬──────────────────────────────────────┘
                                 │
                                 ▼ Handoff: Corrupted Index
  ┌─────────────────────────────────────────────────────────────┐
  │ 3. EVALUATE & QUALITY/FRESHNESS (Đánh giá thiệt hại)        │
  │    Quality Report:   data/quality/corrupted_quality.json    │
  │    Freshness Report: data/quality/corrupted_freshness.json  │
  │    Metrics Output:   data/results/corrupted_metrics.json    │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼ Handoff: Damage Metrics
  ┌─────────────────────────────────────────────────────────────┐
  │ 4. REPAIR (Sửa lỗi dựa trên Data Contract & Re-Index)       │
  │    Output CSV:        data/clean/papers_clean_repaired.csv  │
  │    Collection Name:   "papers-repaired"                     │
  │    Repaired Metrics:  data/results/repaired_metrics.json    │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼ Handoff: All Phase Artifacts
  ┌─────────────────────────────────────────────────────────────┐
  │ 5. COMPARE & REPORT (Tạo báo cáo so sánh 3 trạng thái)      │
  │    Report Path: data/reports/corruption_report.md           │
  └─────────────────────────────────────────────────────────────┘