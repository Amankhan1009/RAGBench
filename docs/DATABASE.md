# RAGBench — Database Schema & Neon PostgreSQL Design
## Tables Overview
- `workspaces`: Multi-tenant boundary.
- `api_keys`: Encrypted BYOK credentials (`encrypted_key`, `provider`, `workspace_id`).
- `datasets`: Evaluation datasets and version history.
- `dataset_items`: Rows containing input, expected output, and ground truth context.
- `experiments`: Benchmark runs linked to datasets and models.
- `evaluation_results`: Per-item evaluation scores, latencies, costs, and traces.
