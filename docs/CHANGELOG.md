# RAGBench — Changelog

## [0.2.0-phase2] - 2026-09-28
### Added
- Neon Cloud PostgreSQL connection support with SSL (`ssl=require`).
- `src/ragbench/db/base.py`: Declarative Base & standard UUID audit mixin.
- `src/ragbench/db/session.py`: Event-loop-aware Async SQLAlchemy engine with pool pre-ping & 300s recycling.
- Updated `/api/v1/health` with live `SELECT 1` database probe.
- Async Alembic database migration environment (`alembic/env.py`).
- Pytest database integration test suite (`tests/test_db.py`).

## [0.1.0-phase1] - 2026-09-28
### Added
- FastAPI application package under `src/ragbench/`.
- Pydantic v2 `BaseSettings` configuration (`config.py`).
- Structured logging configuration (`logging.py`).
- FastAPI `lifespan` context manager.
- Health check API routes (`health.py`).

## [0.1.0-phase0] - 2026-09-28
### Added
- Initialized `docs/AGENTS.md` operating guide and root `README.md`.
- Created 19 core architecture and operational specification files in `docs/`.
- Created `scripts/verify_compatibility_spike.py`.
