# RAGBench — Changelog

## [0.13.0-phase13] - 2026-10-03
### Added
- Created `src/ragbench/models/workspace.py` with `Workspace` and `WorkspaceApiKey` models.
- Created `src/ragbench/schemas/auth.py` for workspace creation, BYOK key registration, and metadata preview.
- Created `src/ragbench/api/v1/auth.py` with `/auth/workspaces`, `/auth/keys`, and `get_current_workspace` dependency.
- Registered auth router in `src/ragbench/main.py`.
- Added `tests/test_auth.py` test suite.
