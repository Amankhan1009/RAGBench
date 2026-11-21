# RAGBench — Current State

- **Current Status:** Version 3.0 IN PROGRESS (Phases 22 & 23 Completed; Phases 1-21 Production Verified)
- **Target Status:** Milestone v3.0 — Enterprise AI Security, Guardrails, Universal Webhook Provider & LLM Gateway ([`docs/V3_SECURITY_ROADMAP.md`](V3_SECURITY_ROADMAP.md))
- **Completed Components (v3.0):**
  - **Phase 22 (Custom HTTP Webhook Provider & Live RAG Pipeline Benchmarking):** Universal `WebhookProvider` (`src/ragbench/providers/webhook.py`) enabling users to connect and benchmark arbitrary external RAG APIs, custom microservices, and proprietary LLM endpoints directly against golden datasets; configurable HTTP headers & Bearer tokens; dot-notation JSON path traversal for response answers (`response_path`) and dynamic retrieved context chunks (`contexts_path`); automatic evaluation of dynamic retrieved contexts in `EvaluationEngine` (hit rate, precision, recall); interactive UI integration in `Run New Evaluation`.
  - **Phase 23 (OpenAI-Compatible AI Gateway, Semantic Cache & Automated Failover):** Universal `/api/v1/gateway/chat/completions` endpoint supporting drop-in OpenAI SDK integration; sub-5ms in-memory and token Jaccard semantic caching delivering **$0.00 cost** on repeated/similar queries; automated provider failover chain (`primary -> fallbacks`) recovering from 429 rate limits or server outages with zero user downtime; workspace monthly USD budget caps and token quotas with automatic 429 quota enforcement; dedicated **AI Gateway (v3.1)** dashboard tab with live playground, cache stats, latency metrics, and budget controls.
- **Completed Components (v2.0):**
  - **Phase 16 (Multi-Tenant Isolation):** Strict workspace-scoped sessions, foreign keys, private datasets/evaluations, delete endpoints, and Render free-tier sleep/wake detector.
  - **Phase 17 (Visual Analytics & Pareto Frontier):** `GET /api/v1/experiments/analytics/pareto` API, 2D Pareto Scatter Plot (Quality vs Latency), 5-Axis Metric Radar (Spider) Chart, and Historical Quality Trendlines.
  - **Phase 18 (Real-Time SSE Streaming):** `POST /api/v1/experiments/stream` SSE endpoint emitting per-sample evaluations, live animated progress bar, rolling ETA ticker, real-time latency/cost meters, and live streaming feed.
  - **Phase 19 (Synthetic AI Test Dataset Generator):** `POST /api/v1/datasets/generate-synthetic` endpoint with support for BYOK LLMs (Groq, OpenAI, Claude, Gemini) and deterministic mock synthesis; interactive dataset builder UI with text upload, 1-10 sample count slider, difficulty distributions (factual, reasoning, adversarial, mixed), inline editing table, and 1-click dataset creation.
  - **Phase 20 (Dataset Ingestion & Executive Reports):** `POST /api/v1/datasets/ingest` bulk ingestion for CSV, JSONL, and JSON with auto-delimiter sniffing and column mapping; download templates; export endpoints (`/export/markdown`, `/export/csv`, `/export/jsonl`); interactive modal for copying GitHub PR Markdown reports, raw CSV/JSONL data downloads, and printable PDF cards.
  - **Phase 21 (Dedicated Agent Trajectory & Loop Inspector UI):** `GET /api/v1/agent/scenarios` and `POST /api/v1/agent/evaluate-trajectory` APIs; interactive multi-step visual flow timeline graph (`Thought -> Action -> Observation -> Final Answer`); infinite loop & redundant call detector; missing expected tool diagnostic alerts; path efficiency scoring.
- **Completed Components (v1.0):**
  - Full hybrid evaluation engine (Deterministic + LLM-as-a-Judge)
  - 100% Model-independent LLM provider abstraction layer (Groq, OpenAI, Anthropic, Google Gemini, Webhook)
  - Bring Your Own Key (BYOK) vault with AES-256 Fernet encryption and inline key resolution
  - Regression detection engine with automated tolerance threshold gating
  - LangSmith tracing integration with automated secret scrubbing and HTTP 202 acceptance
  - Full Next.js 16 frontend dashboard with responsive dark UI
  - Multi-stage Docker packaging (`Dockerfile` with dynamic port binding)
  - Render blueprint deployment configuration (`render.yaml` on Free Tier)
  - Automated GitHub Actions CI/CD pipeline (`.github/workflows/ci.yml`)
- **Verified Test Suite:** 81 unit, integration, analytics, streaming, ingestion, agent trajectory, webhook, and AI Gateway tests passing (100%) + clean TypeScript checks. Complete mathematical specifications documented in [`docs/EVALUATION.md`](EVALUATION.md).
- **Next Milestone:** Milestone v3.0 Phase 24 — NVIDIA NeMo Guardrails Engine (Input/Output/Colang) ([`docs/V3_SECURITY_ROADMAP.md`](V3_SECURITY_ROADMAP.md))


