# RAGBench — System Architecture & Component Design
## Active Modular Monolith Architecture
            ┌──────────────────────────────────────────┐
              │            Next.js Frontend              │
              └────────────────────┬─────────────────────┘
                                   │ REST API (JSON)
              ┌────────────────────▼─────────────────────┐
              │            FastAPI Backend               │
              ├──────────────────────────────────────────┤
              │  Auth │ Datasets │ Experiments │ Metrics  │
              └───────┬──────────────────────────┬───────┘
                      │                          │
       ┌──────────────▼────────────┐  ┌──────────▼────────────┐
       │ Event-Loop Aware Engine   │  │ LLM Provider Interface│
       │ (Asyncpg + Neon Cloud DB) │  │ (Groq/OpenAI/Anth/Ggl)│
       └───────────────────────────┘  └──────────┬────────────┘
                                                 │
                                      ┌──────────▼────────────┐
                                      │ DeepEval Bridge &     │
                                      │ LangSmith Observability│
                                      └───────────────────────┘

## Core Module Layout
- `src/ragbench/core`: `config.py` (Pydantic v2 settings & Neon URL normalizer), `logging.py` (Structured logging).
- `src/ragbench/db`: `base.py` (Declarative Base & UUID mixin), `session.py` (Loop-aware async engine factory).
- `src/ragbench/api/v1`: `health.py` (FastAPI router with active DB probe).
- `src/ragbench/providers`: (Phase 3 abstraction layer).
