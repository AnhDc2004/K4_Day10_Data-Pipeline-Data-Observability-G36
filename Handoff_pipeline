  ┌─────────────────────────────────────────────────────────┐
  │                 1. INGESTION (RAW)                      │
  │  - External Source: Crossref API                        │
  │  - Fetch Payload & Save Raw: data/raw/crossref_raw.json │
  │  - Parse & Save Snapshot: data/raw/crossref_records.json│
  └───────────────────────────┬─────────────────────────────┘
                              │
                              ▼ Handoff: List[PaperRecord]
  ┌─────────────────────────────────────────────────────────┐
  │                 2. TRANSFORMATION (CLEAN)               │
  │  - Clean Abstract / Authors / Categories                │
  │  - Parse ISO Dates & Calculate age_days                 │
  │  - Build text_for_embedding                             │
  │  - Filter noise / duplicates & Export Parquet           │
  └───────────────────────────┬─────────────────────────────┘
                              │
                              ▼ Handoff: Cleaned DataFrame / Parquet
  ┌─────────────────────────────────────────────────────────┐
  │                 3. VECTORIZATION (INDEX)                │
  │  - Load Embedding Model (SentenceTransformers / OpenAI) │
  │  - Generate Vector Embeddings                           │
  │  - Upsert Payload & Vectors to Vector DB (Chroma/Qdrant)│
  └───────────────────────────┬─────────────────────────────┘
                              │
                              ▼ Handoff: Vector Index / Collection
  ┌─────────────────────────────────────────────────────────┐
  │                 4. EVALUATION & OBSERVABILITY           │
  │  - Test Retrieval Quality (Top-k Recall, Precision, MRR)│
  │  - Check Data Drift / Schema / Missing Values           │
  │  - Validate Embedding Distribution                      │
  └───────────────────────────┬─────────────────────────────┘
                              │
                              ▼ Handoff: Metrics & Observability Logs
  ┌─────────────────────────────────────────────────────────┐
  │                 5. REPORTING & DASHBOARD                │
  │  - Generate Execution Summary & Quality Reports         │
  │  - Export Metrics (Prometheus / JSON Report / HTML)     │
  │  - Alert on Failures (Data Quality / Pipeline Drift)    │
  └─────────────────────────────────────────────────────────┘