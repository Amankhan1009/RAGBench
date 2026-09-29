# RAGBench — Current State

- **Active Phase:** Phase 8 — RAG Evaluation Engine & LLM-as-a-Judge (**COMPLETED**)
- **Target Phase:** Phase 9 — Experiments & Baseline Comparison (**READY**)
- **Completed Components:**
  - `LLMJudgeEvaluator` base interface delegating model calls through `BaseLLMProvider`
  - `FaithfulnessEvaluator` (evaluates context support for generated claims)
  - `AnswerRelevancyEvaluator` (evaluates direct query relevancy)
  - `GroundednessEvaluator` (evaluates factual context grounding)
  - `HallucinationEvaluator` (calculates hallucination score & threshold pass rate)
  - `CitationCorrectnessEvaluator` (evaluates in-text source citation accuracy)
  - Live API verification script (`scripts/test_live_llm.py`) tested with Groq Cloud API
  - Unit test suite (`tests/test_llm_judge_evaluators.py`)
- **Verified Test Suite:** 17/17 Pytest unit & integration tests passing.
