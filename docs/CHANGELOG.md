# RAGBench — Changelog

## [0.6.1-refactor] - 2026-09-29
### Refactored
- Removed static `MODEL_PRICING` dictionary to enforce 100% model independence across all LLM providers.
- Created `calculate_token_cost` for dynamic rate-based token cost estimation.
- Updated `docs/AI_MODEL_STRATEGY.md` with model-independent provider documentation.
