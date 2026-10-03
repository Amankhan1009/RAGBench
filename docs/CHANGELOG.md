# RAGBench — Changelog

## [0.14.0-phase14] - 2026-10-03
### Added
- Created `src/ragbench/evaluators/agent/trajectory.py` with `TrajectoryEvaluator`, `ToolCall`, `AgentStep`, and `AgentTrajectory`.
- Implemented loop detection, redundant tool call tracking, precision, recall, and efficiency metrics.
- Created `src/ragbench/api/v1/agent.py` (`POST /api/v1/agent/evaluate-trajectory`).
- Added `tests/test_agent_evaluator.py` covering loops, missing tools, and REST API calls.
