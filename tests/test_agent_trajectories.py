"""Integration test suite for Agent Trajectory Evaluation & Loop Inspector (Phase 21)."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

import ragbench.models  # noqa: F401
from ragbench.db.base import Base
from ragbench.db.session import get_engine
from ragbench.main import app


@pytest.fixture(autouse=True)
async def setup_test_db():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.mark.asyncio
async def test_list_agent_scenarios():
    """Verify endpoint returns benchmark preset scenarios across all diagnostic categories."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Register user
        reg = await client.post(
            "/api/v1/auth/register",
            json={"email": f"agent_scenarios_{uuid.uuid4().hex[:8]}@test.com", "password": "password123", "name": "Agent User"},
        )
        assert reg.status_code == 201
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        res = await client.get("/api/v1/agent/scenarios", headers=headers)
        assert res.status_code == 200
        scenarios = res.json()
        assert len(scenarios) >= 4
        ids = [s["id"] for s in scenarios]
        assert "optimal-research-qa" in ids
        assert "infinite-sql-loop" in ids
        assert "security-mfa-bypass" in ids
        assert "suboptimal-wandering" in ids


@pytest.mark.asyncio
async def test_evaluate_optimal_trajectory():
    """Verify optimal trajectory achieves 100% accuracy, 1.0 efficiency, and passes without loops."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        reg = await client.post(
            "/api/v1/auth/register",
            json={"email": f"agent_opt_{uuid.uuid4().hex[:8]}@test.com", "password": "password123", "name": "Opt User"},
        )
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "trajectory": {
                "goal": "Verify order and dispatch label",
                "steps": [
                    {
                        "step_number": 1,
                        "thought": "Checking status",
                        "tool_call": {"name": "fetch_order", "arguments": {"id": 1}},
                        "observation": "Delivered",
                    },
                    {
                        "step_number": 2,
                        "thought": "Printing label",
                        "tool_call": {"name": "generate_label", "arguments": {"id": 1}},
                        "observation": "LBL-101",
                    },
                ],
                "final_response": "Label generated successfully",
                "success": True,
            },
            "expected_tools": ["fetch_order", "generate_label"],
            "max_optimal_steps": 2,
            "loop_threshold": 2,
        }

        res = await client.post("/api/v1/agent/evaluate-trajectory", headers=headers, json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["passed"] is True
        assert data["loop_detected"] is False
        assert data["redundant_call_count"] == 0
        assert data["tool_selection_accuracy"] == 1.0
        assert data["efficiency_score"] == 1.0
        assert len(data["step_diagnostics"]) == 2
        assert not data["step_diagnostics"][0]["is_loop_duplicate"]


@pytest.mark.asyncio
async def test_evaluate_infinite_loop_trajectory():
    """Verify repeated identical tool calls trigger loop_detected flag and fail verdict."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        reg = await client.post(
            "/api/v1/auth/register",
            json={"email": f"agent_loop_{uuid.uuid4().hex[:8]}@test.com", "password": "password123", "name": "Loop User"},
        )
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "trajectory": {
                "goal": "Execute database query",
                "steps": [
                    {
                        "step_number": 1,
                        "thought": "Running SQL query",
                        "tool_call": {"name": "execute_sql", "arguments": {"q": "SELECT * FROM users"}},
                        "observation": "Error: timeout",
                    },
                    {
                        "step_number": 2,
                        "thought": "Retrying identical SQL query",
                        "tool_call": {"name": "execute_sql", "arguments": {"q": "SELECT * FROM users"}},
                        "observation": "Error: timeout",
                    },
                ],
                "final_response": None,
                "success": False,
            },
            "expected_tools": ["execute_sql"],
            "max_optimal_steps": 2,
            "loop_threshold": 2,
        }

        res = await client.post("/api/v1/agent/evaluate-trajectory", headers=headers, json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["loop_detected"] is True
        assert data["redundant_call_count"] >= 1
        assert data["passed"] is False
        # Diagnostic flagged step 2 as duplicate
        step2 = next(s for s in data["step_diagnostics"] if s["step_number"] == 2)
        assert step2["is_loop_duplicate"] is True


@pytest.mark.asyncio
async def test_evaluate_security_mfa_bypass():
    """Verify skipped expected tools result in precision/recall penalties and missing tool alerts."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        reg = await client.post(
            "/api/v1/auth/register",
            json={"email": f"agent_sec_{uuid.uuid4().hex[:8]}@test.com", "password": "password123", "name": "Sec User"},
        )
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "trajectory": {
                "goal": "Transfer funds",
                "steps": [
                    {
                        "step_number": 1,
                        "thought": "Transferring funds immediately without verification",
                        "tool_call": {"name": "execute_transfer", "arguments": {"amount": 50000}},
                        "observation": "Done",
                    }
                ],
                "final_response": "Transferred",
                "success": True,
            },
            "expected_tools": ["verify_mfa_token", "check_limits", "execute_transfer"],
            "max_optimal_steps": 3,
            "loop_threshold": 2,
        }

        res = await client.post("/api/v1/agent/evaluate-trajectory", headers=headers, json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["tool_recall"] < 0.5  # Only 1 of 3 expected tools was called
        assert data["passed"] is False
        assert "verify_mfa_token" in data["details"]["missing_expected_tools"]
        assert "check_limits" in data["details"]["missing_expected_tools"]


@pytest.mark.asyncio
async def test_evaluate_suboptimal_path_penalty():
    """Verify trajectories taking excess steps are penalized in efficiency score."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        reg = await client.post(
            "/api/v1/auth/register",
            json={"email": f"agent_eff_{uuid.uuid4().hex[:8]}@test.com", "password": "password123", "name": "Eff User"},
        )
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        steps = [
            {
                "step_number": i,
                "thought": f"Wandering search {i}",
                "tool_call": {"name": f"search_{i}", "arguments": {"q": f"query {i}"}},
                "observation": f"res {i}",
            }
            for i in range(1, 7)
        ]

        payload = {
            "trajectory": {
                "goal": "Find CEO",
                "steps": steps,
                "final_response": "Found Jane Doe",
                "success": True,
            },
            "expected_tools": ["search_1", "search_2"],
            "max_optimal_steps": 2,  # 6 steps taken vs 2 optimal -> penalty of 0.4
            "loop_threshold": 3,
        }

        res = await client.post("/api/v1/agent/evaluate-trajectory", headers=headers, json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["total_steps"] == 6
        assert data["efficiency_score"] <= 0.65


@pytest.mark.asyncio
async def test_agent_workspace_unauthenticated_rejection():
    """Verify unauthorized requests with invalid bearer token fail with HTTP 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.get(
            "/api/v1/agent/scenarios",
            headers={"Authorization": "Bearer invalid_expired_token"},
        )
        assert res.status_code == 401
