"""Tests for Pareto Frontier, Multi-Dimensional Radar, and Quality Analytics."""
import pytest
from httpx import ASGITransport, AsyncClient

import ragbench.models
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
async def test_pareto_analytics_empty_workspace():
    """Verify Pareto analytics returns empty structure when no experiments exist."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register user
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={"email": "analytics_empty@test.com", "password": "password123", "name": "Empty User"},
        )
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Query analytics
        res = await client.get("/api/v1/experiments/analytics/pareto", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total_experiments"] == 0
        assert data["points"] == []
        assert data["pareto_frontier"] == []
        assert data["radar_comparison"] is None


@pytest.mark.asyncio
async def test_pareto_frontier_calculation_and_domination():
    """Verify Pareto frontier correctly classifies non-dominated vs dominated models."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register User
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={"email": "pareto_calc@test.com", "password": "password123", "name": "Pareto User"},
        )
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create Dataset
        ds_res = await client.post(
            "/api/v1/datasets",
            headers=headers,
            json={
                "name": "Benchmark QA Dataset",
                "items": [
                    {"query": "What is RAGBench?", "expected_output": "An evaluation platform."},
                    {"query": "What is Pareto optimality?", "expected_output": "Non-dominated trade-off."},
                ],
            },
        )
        assert ds_res.status_code == 201
        dataset_id = ds_res.json()["id"]

        # 3. Create Model A (Baseline): Fast, Moderate accuracy
        exp_a = await client.post(
            "/api/v1/experiments",
            headers=headers,
            json={
                "name": "Model Fast-A",
                "dataset_id": dataset_id,
                "provider_name": "mock",
                "model_name": "fast-model-8b",
            },
        )
        assert exp_a.status_code == 201
        exp_a_id = exp_a.json()["id"]

        # Set Model A as baseline
        await client.post(f"/api/v1/experiments/{exp_a_id}/set-baseline", headers=headers)

        # 4. Create Model B: High Accuracy
        exp_b = await client.post(
            "/api/v1/experiments",
            headers=headers,
            json={
                "name": "Model Smart-B",
                "dataset_id": dataset_id,
                "provider_name": "mock",
                "model_name": "smart-model-70b",
            },
        )
        assert exp_b.status_code == 201
        assert exp_b.json()["id"] is not None

        # 5. Query Pareto analytics
        res = await client.get("/api/v1/experiments/analytics/pareto", headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert data["total_experiments"] == 2
        assert len(data["points"]) == 2
        assert len(data["pareto_frontier"]) >= 1
        assert len(data["trends"]) == 2

        # Verify Radar comparison between Candidate (Model B) and Baseline (Model A)
        assert data["radar_comparison"] is not None
        radar_dims = {d["dimension"] for d in data["radar_comparison"]}
        assert "Faithfulness" in radar_dims
        assert "Latency Efficiency" in radar_dims
        assert "Cost Efficiency" in radar_dims


@pytest.mark.asyncio
async def test_pareto_analytics_workspace_isolation():
    """Verify complete tenant isolation for Pareto analytics between two users."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User 1
        res1 = await client.post(
            "/api/v1/auth/register",
            json={"email": "tenant_1_analytics@test.com", "password": "password123", "name": "Tenant 1"},
        )
        token1 = res1.json()["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        # User 2
        res2 = await client.post(
            "/api/v1/auth/register",
            json={"email": "tenant_2_analytics@test.com", "password": "password123", "name": "Tenant 2"},
        )
        token2 = res2.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # User 1 creates dataset and experiment
        ds1 = await client.post(
            "/api/v1/datasets",
            headers=headers1,
            json={"name": "Tenant 1 Dataset", "items": [{"query": "Q1", "expected_output": "A1"}]},
        )
        await client.post(
            "/api/v1/experiments",
            headers=headers1,
            json={"name": "Tenant 1 Experiment", "dataset_id": ds1.json()["id"], "provider_name": "mock"},
        )

        # User 1 queries analytics: should have 1 experiment
        analytics1 = await client.get("/api/v1/experiments/analytics/pareto", headers=headers1)
        assert analytics1.json()["total_experiments"] == 1

        # User 2 queries analytics: MUST have 0 experiments (Strict Tenant Boundary)
        analytics2 = await client.get("/api/v1/experiments/analytics/pareto", headers=headers2)
        assert analytics2.json()["total_experiments"] == 0
        assert len(analytics2.json()["points"]) == 0
