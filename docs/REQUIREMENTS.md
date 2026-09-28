# RAGBench — Functional & Non-Functional Requirements
## Functional Requirements
- **FR-01:** Encryption of user BYOK credentials before persistent storage.
- **FR-02:** Provider execution support for Groq, OpenAI, Anthropic, and Google.
- **FR-03:** Dataset creation, row parsing, versioning, and JSON/CSV upload.
- **FR-04:** Deterministic metric evaluations: Exact Match, Recall@K, Precision@K, MRR, Hit Rate, Token Usage, Latency.
- **FR-05:** LLM-as-a-judge evaluations: Faithfulness, Relevancy, Groundedness, Hallucination, Citation Correctness.
- **FR-06:** Experiment execution, baseline setting, and delta comparison.
- **FR-07:** CI/CD regression detection blocking PRs when quality drops below threshold.
## Non-Functional Requirements
- **NFR-01:** Sub-50ms API endpoint latency (excluding LLM evaluation execution).
- **NFR-02:** Zero secret leakage in logs, traces, database dumps, or API DTOs.
- **NFR-03:** Partial experiment tolerance: individual LLM timeouts must not fail the full run.
