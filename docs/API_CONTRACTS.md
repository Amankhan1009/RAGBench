# RAGBench — API Contracts Specification
## Core Endpoints
- `GET /api/v1/health`: System health and Neon DB status.
- `POST /api/v1/keys`: Register encrypted BYOK credentials.
- `POST /api/v1/datasets`: Upload new evaluation dataset.
- `POST /api/v1/experiments`: Initiate evaluation experiment run.
- `GET /api/v1/experiments/{id}/compare`: Compare experiment against baseline.
