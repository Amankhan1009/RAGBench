# RAGBench — Reliability & Resilience Design
## Mitigation Mechanisms
1. **Exponential Backoff:** Retries with full jitter for rate-limited (HTTP 429) requests.
2. **Connection Recycling:** Neon database connection pool recycling every 300s.
3. **Concurrency Semaphore:** Bound active concurrent LLM judge calls to avoid rate exhaustion.
