# RAGBench — Changelog

## [0.11.0-phase11] - 2026-10-03
### Added
- Created `src/ragbench/core/tracing.py` (`TraceManager`, `TraceSpan`, `redact_text`, `sanitize_payload`, `trace_async_run`).
- Updated `src/ragbench/core/logging.py` with `SecretRedactingFilter` to auto-sanitize logs.
- Added `tests/test_tracing.py` test suite with 5 test cases.

## [0.10.0-phase10] - 2026-09-30
### Added
- Created `src/ragbench/evaluators/regression.py` (`RegressionDetector` & `RegressionReport`).
- Updated `src/ragbench/api/v1/experiments.py` with `GET /experiments/{id}/check-regression` endpoint.
- Created `scripts/check_regression.py` standalone CI gate script.
- Updated `scripts/test_live_llm.py` to test live regression gates against Groq Cloud API.
- Added `tests/test_regression.py` test suite (20/20 tests passing).
