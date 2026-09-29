# RAGBench — Changelog

## [0.7.0-phase7] - 2026-09-29
### Added
- Created `src/ragbench/evaluators/base.py` (`EvaluationResult` DTO and `BaseEvaluator` ABC).
- Created deterministic evaluators: `ExactMatchEvaluator`, `RecallAtKEvaluator`, `PrecisionAtKEvaluator`, `MRREvaluator`, `HitRateEvaluator`, `ContextOverlapEvaluator`, `LatencyTokenEvaluator`.
- Created `src/ragbench/evaluators/engine.py` (`EvaluationEngine` batch orchestrator).
- Added `tests/test_deterministic_evaluators.py` test suite (14/14 tests passing).
- Added `.kilo/` to `.gitignore`.
