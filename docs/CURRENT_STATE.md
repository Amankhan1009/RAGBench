# RAGBench — Current State

- **Current Status:** Version 2.0 In Progress (Phases 16 & 17 Completed)
- **Target Status:** Implement Version 2.0 Roadmap ([`docs/V2_ROADMAP.md`](V2_ROADMAP.md))
- **Completed Components (v2.0):**
  - **Phase 16 (Multi-Tenant Isolation):** Strict workspace-scoped sessions, foreign keys, private datasets/evaluations, delete endpoints, and Render free-tier sleep/wake detector.
  - **Phase 17 (Visual Analytics & Pareto Frontier):** `GET /api/v1/experiments/analytics/pareto` API, 2D Pareto Scatter Plot (Quality vs Latency), 5-Axis Metric Radar (Spider) Chart, and Historical Quality Trendlines.
- **Completed Components (v1.0):**
  - Full hybrid evaluation engine (Deterministic + LLM-as-a-Judge)
  - 100% Model-independent LLM provider abstraction layer (Groq, OpenAI, Anthropic, Google Gemini)
  - Bring Your Own Key (BYOK) vault with AES-256 Fernet encryption and inline key resolution
  - Regression detection engine with automated tolerance threshold gating
  - LangSmith tracing integration with automated secret scrubbing and HTTP 202 acceptance
  - Full Next.js 16 frontend dashboard with responsive dark UI
  - Multi-stage Docker packaging (`Dockerfile` with dynamic port binding)
  - Render blueprint deployment configuration (`render.yaml` on Free Tier)
  - Automated GitHub Actions CI/CD pipeline (`.github/workflows/ci.yml`)
- **Verified Test Suite:** 40/40 unit, integration, analytics, and regression tests passing + clean TypeScript checks.
- **Next Milestone:** Phase 18 — Real-Time Streaming & Live Evaluation Progress (Server-Sent Events)
