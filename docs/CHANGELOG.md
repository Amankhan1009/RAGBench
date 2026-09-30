# RAGBench — Changelog

## [0.9.0-phase9] - 2026-09-30
### Added
- Created `src/ragbench/models/experiment.py` (`Experiment` & `ExperimentItem` models).
- Created `src/ragbench/schemas/experiment.py` (`ExperimentCreate`, `ExperimentResponse`, `ComparisonDelta`).
- Created `src/ragbench/api/v1/experiments.py` (REST endpoints for launching runs, setting baselines, and delta comparisons).
- Added `tests/test_experiments.py` integration test suite (18/18 tests passing).
