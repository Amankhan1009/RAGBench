# RAGBench — Architecture Decision Records (ADRs)
## ADR-001: Cloud-Only Neon PostgreSQL Database
- **Decision:** Use Neon PostgreSQL cloud database via `DATABASE_URL` with SSL connection (`sslmode=require`).
- **Rationale:** Eliminates local database drift and matches production environment.
- **Consequences:** Async engine must handle auto-suspend connection recycling (`pool_pre_ping=True`, `pool_recycle=300`).
## ADR-002: Unified LLM Provider Abstraction & BYOK Encryption
- **Decision:** All LLM model requests must route through `BaseLLMProvider`. API keys are encrypted at rest using AES-256/Fernet.
- **Rationale:** Ensures credentials are never stored in plain text, logged, or exposed.
## ADR-003: DeepEval Provider Bridge Strategy
- **Decision:** DeepEval metrics execute via custom metric classes wrapping `BaseLLMProvider`.
- **Rationale:** Prevents DeepEval from bypassing RAGBench security, rate limiting, and auditing.
