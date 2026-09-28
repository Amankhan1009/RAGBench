# RAGBench — Failure Scenarios & Taxonomy
- **FS-01 Invalid API Key:** Returns HTTP 400 with sanitized error; does not retry.
- **FS-02 Provider Rate Limit (429):** Retries up to 5 times with exponential backoff.
- **FS-03 Model Output Parsing Failure:** Marks item status as `FAILED_PARSING`, records raw output, continues evaluation run.
- **FS-04 Neon Database Disconnect:** Auto-reconnects via SQLAlchemy `pool_pre_ping`.
