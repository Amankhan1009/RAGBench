# AGENTS.md — RAGBench AI Assistant Operating Guide
Welcome to **RAGBench**, a production-grade LLM + RAG Evaluation & Benchmarking Platform.
## 1. Frozen Stack & Infrastructure Constraints
### Core Tech Stack
- **Backend:** Python 3.13+, FastAPI, Pydantic v2, SQLAlchemy 2.x (Async), Alembic
- **Database:** Neon PostgreSQL (Cloud Only via `DATABASE_URL`). Connection SSL `sslmode=require`.
- **Frontend:** Next.js, React, TypeScript, Tailwind CSS, shadcn/ui
- **Evaluation:** DeepEval, Custom Evaluation Engine, Deterministic Metrics, LLM-as-a-Judge
- **Providers:** Groq, OpenAI, Anthropic, Google (via Unified Provider Abstraction)
- **Observability:** LangSmith
- **Quality & Ops:** Pytest, Ruff, Docker, GitHub Actions
### STRICT CLOUD-ONLY RULES
- **Database:** Cloud Neon PostgreSQL ONLY. NEVER use SQLite, local PostgreSQL, or PostgreSQL Docker containers.
- **LLMs:** Cloud APIs ONLY (Groq, OpenAI, Anthropic, Google). NEVER use Ollama, LM Studio, or local models.
- **BYOK (Bring Your Own Key):** Users supply encrypted API keys per request/workspace. Plaintext API keys must NEVER be logged, stored in plaintext, exported to frontend, or committed to Git.
## 2. LLM Provider Architecture
All LLM operations must route through RAGBench's Unified Provider Abstraction (`BaseLLMProvider`):
Evaluation Engine / DeepEval Spike ↓ LLM Provider Interface (BaseLLMProvider) ↓ ├── GroqProvider ├── OpenAIProvider ├── AnthropicProvider └── GoogleProvider



- **DeepEval Integration Rule:** DeepEval MUST NOT bypass the RAGBench provider interface. Custom metric drivers must delegate model calls through `BaseLLMProvider`.
## 3. Mandatory Milestone Workflow Rules
When working on RAGBench, every milestone follows this strict sequence:
1. Explain what is being built, why, how, and where it fits.
2. Show only the relevant file/folder tree.
3. Specify exact files to create/modify.
4. Provide code directly in chat (one file at a time).
5. Provide exact verification commands.
6. **STOP** and wait for user terminal/test output.
7. Verify output. If PASS, update docs and provide Milestone Handoff.
## 4. Documentation Lifecycle
After completing EVERY milestone, update at minimum:
- `docs/CURRENT_STATE.md`
- `docs/MILESTONES.md`
- `docs/CHANGELOG.md`
- `docs/TODO.md`
`CURRENT_STATE.md` must always enable any AI developer to immediately resume work without context loss.
