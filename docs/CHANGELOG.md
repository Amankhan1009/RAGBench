# RAGBench — Changelog

## [0.5.0-phase5] - 2026-09-28
### Added
- Created `src/ragbench/providers/openai.py` (`OpenAIProvider`).
- Created `src/ragbench/providers/anthropic.py` (`AnthropicProvider`).
- Created `src/ragbench/providers/google.py` (`GoogleProvider`).
- Created `estimate_token_cost` dynamic token pricing estimator.
- Refactored `ProviderFactory` to support model-independent dynamic selection across 5 providers.
- Added `tests/test_multi_providers.py`.
