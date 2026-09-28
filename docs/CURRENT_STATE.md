# RAGBench — Current State

- **Active Phase:** Phase 6 — Dataset & Version Management (**COMPLETED**)
- **Target Phase:** Phase 7 — Core Evaluation Engine (**WAITING FOR CONFIRMATION**)
- **Completed Components:**
  - `Dataset` and `DatasetItem` SQLAlchemy 2.x ORM models (`src/ragbench/models/dataset.py`)
  - Pydantic v2 Dataset schemas for creation, bulk import, and API DTOs (`src/ragbench/schemas/dataset.py`)
  - Dataset REST API endpoints (`POST /datasets`, `GET /datasets`, `GET /datasets/{id}`, `POST /datasets/{id}/items`)
  - Auto-table migration on application startup in FastAPI lifespan context
  - Integration test suite verifying dataset lifecycle (`tests/test_datasets.py`)
- **Verified Test Suite:** 9/9 Pytest unit & integration tests passing.
