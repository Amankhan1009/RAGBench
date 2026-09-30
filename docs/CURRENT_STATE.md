# RAGBench — Current State

- **Active Phase:** Phase 9 — Experiments & Baseline Comparison (**COMPLETED**)
- **Target Phase:** Phase 10 — Regression Testing & Automated CI Gates (**READY**)
- **Completed Components:**
  - `Experiment` & `ExperimentItem` SQLAlchemy 2.x ORM models (`src/ragbench/models/experiment.py`)
  - Pydantic v2 schemas for experiment execution, item results, and delta comparison DTOs (`src/ragbench/schemas/experiment.py`)
  - REST API endpoints (`POST /experiments`, `GET /experiments/{id}`, `POST /experiments/{id}/set-baseline`, `GET /experiments/{id}/compare`)
  - Active baseline tracking per dataset and automated metric delta calculation (+/- candidate vs baseline)
  - Integration test suite (`tests/test_experiments.py`)
- **Verified Test Suite:** 18/18 Pytest unit & integration tests passing.
