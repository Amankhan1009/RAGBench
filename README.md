# ⚡ RAGBench

### Production-Grade LLM, RAG & Agent Continuous Evaluation Platform

<div align="center">

[![CI Verification](https://img.shields.io/badge/CI%20Verification-100%25%20Passing-success?style=for-the-badge&logo=githubactions)](docs/V1_TESTING_GUIDE.md)
[![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.13+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js 14](https://img.shields.io/badge/Next.js%2014-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)

[![Neon PostgreSQL](https://img.shields.io/badge/Neon_PostgreSQL-00E599?style=for-the-badge&logo=postgresql&logoColor=black)](https://neon.tech)
[![LangSmith](https://img.shields.io/badge/LangSmith-Observability-FF6B35?style=for-the-badge&logo=langchain&logoColor=white)](https://smith.langchain.com/)
[![LangChain](https://img.shields.io/badge/LangChain-Integration-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain.com/)
[![DeepEval](https://img.shields.io/badge/DeepEval-Framework-8A2BE2?style=for-the-badge)](https://confident-ai.com/)
[![Groq LPU](https://img.shields.io/badge/Groq_LPU-Ultra--Fast_Inference-F04438?style=for-the-badge)](https://groq.com)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

</div>

> 🛡️ **Automated CI/CD Regression Defense** &nbsp;|&nbsp; ⚡ **Ultra-Fast Multi-Provider Inference (Groq, OpenAI, Claude, Gemini)** &nbsp;|&nbsp; 🔭 **Zero-Leakage Observability via LangSmith & LangChain**

---

## 🌟 Overview

**RAGBench** is an enterprise-grade evaluation, regression testing, and observability platform designed for LLMs, Retrieval-Augmented Generation (RAG) pipelines, and autonomous AI agents. 

Similar to how traditional software engineering uses automated unit tests and CI/CD pipelines to catch bugs before release, **RAGBench enables engineering teams to continuously benchmark candidate models against golden baselines**, automatically enforcing quality, latency, and cost tolerance budgets to **block regressions before they hit production**.

Powered by **LangSmith & LangChain** for diagnostic tracing, **Groq LPU Cloud** for sub-second inference, **DeepEval** for AI judge frameworks, **FastAPI & Async SQLAlchemy** for high-throughput batch evaluation, and **Next.js 14** for a reactive real-time dashboard.

---

## ✨ Core Capabilities

- 🛡️ **Automated CI/CD Quality Gates:** Compare candidate models against active golden baselines within a strict $\pm2.0\%$ tolerance budget. Automatically issue `APPROVED` or `BLOCKED` verdicts.
- ⚡ **Unified BYOK Provider Abstraction:** Seamless multi-provider support for **Groq LPU**, **OpenAI**, **Anthropic Claude**, **Google Gemini**, and a deterministic **Mock Provider** for zero-cost offline testing.
- 📐 **Hybrid Evaluation Engine:**
  - **Deterministic Metrics:** Exact Match, Context Hit Rate, Context Precision, Latency Budget, and Token Costs.
  - **LLM-as-a-Judge Criteria:** Faithfulness, Answer Relevancy, Groundedness, Hallucination Detection, and Citation Correctness.
- 🤖 **Agentic Trajectory & Infinite Loop Inspector:** Multi-step tool call verification, tool precision/recall scoring, and automated detection of infinite tool recursion.
- 🔐 **Zero-Leakage Security Perimeter:** BYOK API keys are encrypted at rest with **AES-256 Fernet**. Diagnostic traces and logs automatically scrub sensitive credentials with `[REDACTED_SECRET]`.
- 🔭 **End-to-End Tracing & Observability:** Native LangSmith integration captures complete run spans, latencies, tokens, and cost tracking.

---

## 🛠️ Languages, Frameworks & Tech Stack

```
                          ┌────────────────────────────────────────────────────────┐
                          │               RAGBench Web Dashboard                   │
                          │        (Next.js 14 • React 18 • Tailwind CSS)          │
                          └──────────────────────────┬─────────────────────────────┘
                                                     │ HTTP REST / JWT
                          ┌──────────────────────────▼─────────────────────────────┐
                          │                FastAPI REST Gateway                    │
                          │            (Async Pydantic v2 • Python 3.12+)          │
                          └───────┬──────────────────┬─────────────────────┬───────┘
                                  │                  │                     │
                ┌─────────────────▼────────┐ ┌───────▼─────────────┐ ┌─────▼─────────────────┐
                │    Evaluation Engine     │ │   Security Perimeter │ │    Provider Adapter     │
                │ • Deterministic Suite    │ │ • AES-256 Fernet     │ │ • Groq Cloud (LPU)      │
                │ • LLM-as-a-Judge         │ │ • Multi-Tenant JWT   │ │ • OpenAI / Anthropic    │
                │ • Agent Loop Detection   │ │ • Secret Redaction   │ │ • Google Gemini / Mock  │
                └──────────────────────────┘ └──────────────────────┘ └─────────────────────────┘
                                  │                                        │
                          ┌───────▼────────────────────────────────────────▼───────┐
                          │     Neon PostgreSQL Serverless (SQLAlchemy 2.0 Async)  │
                          └────────────────────────────────────────────────────────┘
```

| Domain | Technology / Library | Role & Purpose |
| :--- | :--- | :--- |
| **Backend API** | `FastAPI`, `Uvicorn`, `Pydantic v2` | High-performance asynchronous REST API gateway and validation |
| **Language** | `Python 3.12 / 3.13+` | Modern asynchronous Python engine |
| **Database & ORM** | `Neon PostgreSQL`, `SQLAlchemy 2.0 Async`, `asyncpg` | Cloud-native serverless relational persistence and migrations |
| **Frontend UI** | `Next.js 14`, `React 18`, `TypeScript`, `Tailwind CSS` | Modern reactive single-page dashboard with dark theme UI |
| **Cryptography** | `cryptography` (Fernet AES-256), `PyJWT`, `passlib` | Multi-tenant auth, tamper-proof sessions, encrypted key vaults |
| **LLM Inference** | `httpx` (Async HTTP), `Groq LPU`, `OpenAI`, `Anthropic`, `Google Gemini` | High-throughput provider abstraction with model switching |
| **Evaluation** | `DeepEval` + Custom `EvaluationEngine` | Hybrid deterministic and judge-based scoring pipelines |
| **Observability** | `LangSmith API`, `LangChain RunTree`, Custom Scrubbing Tracers | Distributed run tracing, latency spans, and zero credential leakage |
| **Testing & CI** | `Pytest`, `pytest-asyncio`, `Ruff` | 31-suite unit tests, linting, and automated E2E platform checks |
| **Deployment** | `Docker`, `Render Cloud Blueprint` | Production containerization and PaaS orchestration |

---

## 📚 Complete Documentation Index

Every architecture decision, schema, API contract, and operational manual is fully documented inside the [`docs/`](docs/) directory:

### 🏛️ Architecture & System Design
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — System architecture, component relationships & data flow.
- [`docs/ARCHITECTURE_DECISIONS.md`](docs/ARCHITECTURE_DECISIONS.md) — Architecture Decision Records (ADRs).
- [`docs/PROJECT_OVERVIEW.md`](docs/PROJECT_OVERVIEW.md) — Mission statement, value proposition & core architecture.
- [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) — Functional and non-functional engineering requirements.
- [`docs/RELIABILITY_DESIGN.md`](docs/RELIABILITY_DESIGN.md) — Fault tolerance, retries, exponential backoff & rate limiting.

### 🔌 APIs, Models & Database
- [`docs/API_CONTRACTS.md`](docs/API_CONTRACTS.md) — Complete REST API specifications & Pydantic schemas.
- [`docs/AI_MODEL_STRATEGY.md`](docs/AI_MODEL_STRATEGY.md) — LLM provider abstraction, cost modeling & BYOK key vaults.
- [`docs/DATABASE.md`](docs/DATABASE.md) — Neon PostgreSQL schema definitions, indexes & constraints.
- [`docs/EVALUATION.md`](docs/EVALUATION.md) — Mathematical formulations for deterministic & judge evaluators.
- [`docs/AGENTS.md`](docs/AGENTS.md) — Agentic trajectory benchmarking and loop detection architecture.

### 🧪 Quality, Verification & Operations
- [**`docs/V1_TESTING_GUIDE.md`**](docs/V1_TESTING_GUIDE.md) — **Complete 19-point End-to-End Verification Manual & Results.**
- [`docs/TESTING_STRATEGY.md`](docs/TESTING_STRATEGY.md) — Test pyramid, unit/integration strategies & execution plans.
- [`docs/FAILURE_SCENARIOS.md`](docs/FAILURE_SCENARIOS.md) — Failure taxonomy, circuit breaking & graceful degradation.
- [`docs/FAILURE_DEMONSTRATION.md`](docs/FAILURE_DEMONSTRATION.md) — Reproducible scripts demonstrating failure handling.
- [`docs/OPERATIONS_RUNBOOK.md`](docs/OPERATIONS_RUNBOOK.md) — Production operations, health probes & troubleshooting guide.
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — Production deployment to Render and environment configurations.

### 🚀 Roadmaps & Release Management
- [**`docs/V2_ROADMAP.md`**](docs/V2_ROADMAP.md) — **Version 2.0 Feature Specifications (Pareto frontier, SSE, synthetic data).**
- [`docs/PROJECT_ROADMAP.md`](docs/PROJECT_ROADMAP.md) — Multi-phase project delivery timeline.
- [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md) — Milestone status and release readiness matrix.
- [`docs/CHANGELOG.md`](docs/CHANGELOG.md) — Historical chronological record of codebase enhancements.
- [`docs/MILESTONES.md`](docs/MILESTONES.md) — Milestone acceptance criteria and completion records.
- [`docs/TODO.md`](docs/TODO.md) — Active backlog and engineering task tracking.

---

## 🚦 Verified Test Results (v1.0 Milestone)

Before cloud deployment, **all 19 subsystems passed 100% end-to-end verification**:

```
=================================================================
 🎉 ALL SUBSYSTEMS VERIFIED: 100% PASSING END-TO-END!
=================================================================
 [1/8] Database schema initialization      --> ✅ PASS
 [2/8] Health endpoint (/api/v1/health)    --> ✅ PASS
 [3/8] Multi-tenant BYOK Encryption        --> ✅ PASS
 [4/8] Dataset creation & bulk ingestion   --> ✅ PASS (10 items)
 [5/8] Baseline experiment execution       --> ✅ PASS
 [6/8] Candidate evaluation & comparison   --> ✅ PASS
 [7/8] CI/CD Regression Quality Gate       --> ✅ APPROVED / BLOCKED
 [8/8] Agent Trajectory & Loop Detection   --> ✅ PASS
 [BONUS] Zero-Leakage Secret Redaction     --> ✅ PASS ([REDACTED_SECRET])
=================================================================
```
*See the full report in [`docs/V1_TESTING_GUIDE.md`](docs/V1_TESTING_GUIDE.md).*

---

## ⚡ Quickstart (Local Development)

### 1. Prerequisites
- Python `3.12` or `3.13`
- Node.js `20+` and `npm`

### 2. Backend Setup
```bash
# Clone the repository
git clone https://github.com/Amankhan1009/RAGBench.git
cd RAGBench

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run backend development server
PYTHONPATH=src uvicorn ragbench.main:app --reload --host 0.0.0.0 --port 8000
```
API Documentation will be live at: **[http://localhost:8000/docs](http://localhost:8000/docs)**

### 3. Frontend Setup
```bash
# In a new terminal window
cd frontend
npm install
npm run dev
```
Web Dashboard will be live at: **[http://localhost:3000](http://localhost:3000)**

### 4. Running Automated Tests
```bash
# Run complete unit and security test suite
DATABASE_URL="sqlite+aiosqlite:///:memory:" \
ENCRYPTION_KEY="dGhpcy1pcy1hLXRlc3QtZW5jcnlwdGlvbi1rZXktMTIzNDU=" \
PYTHONPATH=src \
pytest tests/ -v
```

---

## 🔮 Coming in Version 2.0

Following production deployment to Render, development begins on **v2.0**:
1. **Interactive Visual Analytics & Pareto Frontier:** Cost/speed vs quality scatter plots and 6-axis metric radar charts.
2. **Real-Time SSE Streaming:** Live progress bar with streaming token counts, latency, and sample evaluations.
3. **Synthetic AI Test Dataset Generator:** Automatically generate multi-hop queries, contexts, and answers from raw documentation.
4. **Drag-and-Drop Ingestion & Reports:** Import CSV / JSONL benchmark datasets and export executive PDF/Markdown summaries.
5. **Visual Agent Trajectory Inspector:** Interactive thought-tool-action timeline graphs with automated anomaly detection.

*Full architectural specs available in [`docs/V2_ROADMAP.md`](docs/V2_ROADMAP.md).*

---

## 📄 License
This project is licensed under the MIT License.