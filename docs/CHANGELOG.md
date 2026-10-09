# RAGBench — Changelog

## [1.0.0] - 2026-10-09
### Added
- Complete End-to-End Verification Manual & Report (`docs/V1_TESTING_GUIDE.md`) with 19/19 subsystems verified.
- Real cloud LLM evaluation with Groq LPU (`openai/gpt-oss-120b`) across 10-item benchmark dataset.
- Real-to-real LLM CI Regression Gate evaluation (Approved & Blocked verdicts verified).
- Agent Trajectory and Infinite Loop detection engine with Swagger UI verification.
- Version 2.0 Product & Technical Roadmap (`docs/V2_ROADMAP.md`) covering Phases 16-20.

### Fixed
- Fixed BYOK vault key resolution in `ExperimentCreate` schema so omitted API keys correctly trigger encrypted vault lookup for non-mock providers.

### Changed
- Upgraded `README.md` with complete architecture diagram, tech stack breakdown, hero badges (LangSmith, LangChain, Groq, DeepEval, Docker), and documentation index.
- Configured Render Blueprint (`render.yaml`) for automated free-tier cloud deployment.

## [0.15.0-phase15] - 2026-10-03
### Added
- Created production multi-stage backend `Dockerfile` and `.dockerignore`.
- Created production multi-stage frontend `frontend/Dockerfile` and `frontend/.dockerignore`.
- Created `docker-compose.yml` orchestrating backend and frontend services.
- Created `.github/workflows/ci.yml` automating Ruff linting, Pytest test execution, CI regression gate validation, and Next.js production builds.
