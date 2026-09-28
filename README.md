# RAGBench — Production-Grade LLM & RAG Evaluation Platform

**RAGBench** is a production-grade LLM, RAG, and Agent evaluation and benchmarking platform built for continuous quality assessment, regression detection, experiment comparison, and automated CI/CD evaluation gates.

---

## Key Capabilities

- **Unified LLM Provider Abstraction:** Seamless BYOK (Bring Your Own Key) integration across Groq, OpenAI, Anthropic, and Google.
- **Deterministic & LLM-as-a-Judge Evaluation:** Hybrid evaluation engine combining exact/metric math (Exact Match, Recall@K, Precision@K, MRR, Hit Rate, Token Usage, Latency) with LLM-judged criteria (Faithfulness, Relevancy, Hallucination, Groundedness, Citation Correctness).
- **DeepEval Integration:** Framework integration with custom LLM provider bridges enforcing security, rate-limiting, and encrypted credentials.
- **Experiments & Regression Gates:** Track evaluation baselines across dataset versions and automatically block regressions in CI/CD.
- **LangSmith Tracing:** Full LLM/evaluation observability without secret leakage.
- **Cloud-Only Infrastructure:** Built on Neon PostgreSQL and cloud LLM providers.

---

## Frozen Technology Stack

- **Backend:** Python 3.13+, FastAPI, Pydantic v2, Async SQLAlchemy 2.x, Alembic
- **Database:** Neon PostgreSQL (Cloud Only via SSL `DATABASE_URL`)
- **Frontend:** Next.js, React, TypeScript, Tailwind CSS, shadcn/ui
- **Evaluation:** DeepEval + Custom RAGBench Evaluation Engine
- **Observability:** LangSmith
- **Quality & DevOps:** Pytest, Ruff, Docker, GitHub Actions

---

## Documentation Index

All architecture specifications, system designs, and operational runbooks are maintained inside the `docs/` directory:

| Document | Purpose |
| :--- | :--- |
| [`docs/AGENTS.md`](docs/AGENTS.md) | AI Assistant Operating & Workflow Guide |
| [`docs/PROJECT_OVERVIEW.md`](docs/PROJECT_OVERVIEW.md) | High-level system overview & value proposition |
| [`docs/PROJECT_ROADMAP.md`](docs/PROJECT_ROADMAP.md) | Master development roadmap & phases |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture & component design |
| [`docs/ARCHITECTURE_DECISIONS.md`](docs/ARCHITECTURE_DECISIONS.md) | Architecture Decision Records (ADRs) |
| [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) | Functional & non-functional requirements |
| [`docs/API_CONTRACTS.md`](docs/API_CONTRACTS.md) | REST API schemas & endpoints specification |
| [`docs/AI_MODEL_STRATEGY.md`](docs/AI_MODEL_STRATEGY.md) | Provider abstraction & BYOK encryption strategy |
| [`docs/EVALUATION.md`](docs/EVALUATION.md) | Deterministic & LLM-as-a-judge metric specifications |
| [`docs/DATABASE.md`](docs/DATABASE.md) | Neon PostgreSQL schemas & migration guidelines |
| [`docs/RELIABILITY_DESIGN.md`](docs/RELIABILITY_DESIGN.md) | Resilience, backoff, timeouts, and rate limits |
| [`docs/FAILURE_SCENARIOS.md`](docs/FAILURE_SCENARIOS.md) | Failure taxonomy & fallback behaviors |
| [`docs/FAILURE_DEMONSTRATION.md`](docs/FAILURE_DEMONSTRATION.md) | Verification scripts for edge cases & failures |
| [`docs/OPERATIONS_RUNBOOK.md`](docs/OPERATIONS_RUNBOOK.md) | Operational runbooks & troubleshooting guide |
| [`docs/TESTING_STRATEGY.md`](docs/TESTING_STRATEGY.md) | Pytest, unit, integration, and evaluation test plan |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Docker & GitHub Actions CI/CD deployment guide |
| [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md) | Active milestone status & implementation details |
| [`docs/MILESTONES.md`](docs/MILESTONES.md) | Milestone execution log & progress tracking |
| [`docs/CHANGELOG.md`](docs/CHANGELOG.md) | Historical record of code & documentation changes |
| [`docs/TODO.md`](docs/TODO.md) | Action items & pending tasks tracking |

---

## Quick Start (Development)

### Requirements
- Python 3.13+
- `uv` or Python `venv`
- Node.js 20+

### Setup

```bash
# Initialize virtual environment with Python 3.13
uv venv --python 3.13
source .venv/bin/activate