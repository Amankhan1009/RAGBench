# RAGBench — Changelog

## [0.8.0-phase8] - 2026-09-29
### Added
- Created `src/ragbench/evaluators/llm_judge/base.py` (`LLMJudgeEvaluator`).
- Created LLM-as-a-Judge evaluators: `FaithfulnessEvaluator`, `AnswerRelevancyEvaluator`, `GroundednessEvaluator`, `HallucinationEvaluator`, `CitationCorrectnessEvaluator`.
- Created `scripts/test_live_llm.py` for live API invocation testing against cloud providers.
- Added `tests/test_llm_judge_evaluators.py` test suite (17/17 tests passing).
