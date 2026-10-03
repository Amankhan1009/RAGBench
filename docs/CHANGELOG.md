# RAGBench — Changelog

## [0.15.0-phase15] - 2026-10-03
### Added
- Created production multi-stage backend `Dockerfile` and `.dockerignore`.
- Created production multi-stage frontend `frontend/Dockerfile` and `frontend/.dockerignore`.
- Created `docker-compose.yml` orchestrating backend and frontend services.
- Created `.github/workflows/ci.yml` automating Ruff linting, Pytest test execution, CI regression gate validation, and Next.js production builds.
