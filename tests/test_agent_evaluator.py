"""Tests for Agent Trajectory Evaluation Engine and REST API."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

import ragbench.models  # noqa: F401
from ragbench.db.base import Base
from ragbench.db.session import get_engine
from ragbench.evaluators.agent.trajectory import (
    AgentStep,
    AgentTrajectory,
    ToolCall,
    TrajectoryEvaluator,
)
from ragbench.main import app


@pytest.fixture(autouse=True)
async def setup_test_db():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


def test_optimal_agent_trajectory():
    evaluator = TrajectoryEvaluator()
    trajectory = AgentTrajectory(
        goal="Calculate company margin",
        steps=[
            AgentStep(step_number=1, tool_call=ToolCall(name="db_query", arguments={"query": "SELECT revenue"})),
            AgentStep(step_number=2, tool_call=ToolCall(name="calculator", arguments={"expr": "1000 - 800"})),
        ],
        final_response="Margin is $200",
    )
    report = evaluator.evaluate(
        trajectory,
        expected_tools=["db_query", "calculator"],
        max_optimal_steps=3,
    )
    assert report.passed is True
    assert report.loop_detected is False
    assert report.tool_selection_accuracy == 1.0
    assert report.tool_precision == 1.0
    assert report.tool_recall == 1.0
    assert report.redundant_call_count == 0


def test_agent_stuck_in_loop():
    evaluator = TrajectoryEvaluator(loop_threshold=2)
    trajectory = AgentTrajectory(
        goal="Fetch live stock price",
        steps=[
            AgentStep(step_number=1, tool_call=ToolCall(name="fetch_ticker", arguments={"ticker": "AAPL"})),
            AgentStep(step_number=2, tool_call=ToolCall(name="fetch_ticker", arguments={"ticker": "AAPL"})),
        ],
    )
    report = evaluator.evaluate(trajectory)
    assert report.loop_detected is True
    assert report.passed is False
    assert report.redundant_call_count >= 1


def test_agent_missing_expected_tools():
    evaluator = TrajectoryEvaluator()
    trajectory = AgentTrajectory(
        goal="Search and summarize article",
        steps=[
            AgentStep(step_number=1, tool_call=ToolCall(name="search_web", arguments={"q": "AI news"})),
        ],
    )
    report = evaluator.evaluate(
        trajectory,
        expected_tools=["search_web", "summarize_text"],
    )
    assert report.tool_precision == 1.0
    assert report.tool_recall == 0.5  # Only 1 of 2 called
    assert report.passed is False


@pytest.mark.asyncio
async def test_agent_trajectory_api_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        reg = await client.post(
            "/api/v1/auth/register",
            json={"email": f"agent_eval_{uuid.uuid4().hex[:8]}@test.com", "password": "password123", "name": "Eval User"},
        )
        assert reg.status_code == 201
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        res = await client.post(
            "/api/v1/agent/evaluate-trajectory",
            headers=headers,
            json={
                "trajectory": {
                    "goal": "Test API goal",
                    "steps": [
                        {"step_number": 1, "tool_call": {"name": "search", "arguments": {"q": "FastAPI"}}}
                    ],
                },
                "expected_tools": ["search"],
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["passed"] is True
        assert data["tool_selection_accuracy"] == 1.0
