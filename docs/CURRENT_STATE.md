# RAGBench — Current State

- **Active Phase:** Phase 10 — Regression Testing & Automated CI Gates (**COMPLETED**)
- **Target Phase:** Phase 11 — LangSmith Observability & Secret Redaction (**READY**)
- **Completed Components:**
  - `RegressionDetector` engine (`src/ragbench/evaluators/regression.py`)
  - `RegressionReport` Pydantic DTO (has_regression, regressed_metrics, tolerance, details)
  - REST API endpoint (`GET /experiments/{id}/check-regression`)
  - Standalone CI/CD regression gate script (`scripts/check_regression.py`)
  - Live LLM API & Regression verification script (`scripts/test_live_llm.py`)
  - Integration test suite (`tests/test_regression.py`)
- **Verified Test Suite:** 20/20 Pytest unit & integration tests passing + Live Groq API verification passing.
