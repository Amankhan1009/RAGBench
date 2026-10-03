"""Integration test suite for Experiment execution and Baseline comparisons."""
import pytest
from httpx import ASGITransport, AsyncClient

import ragbench.models
from ragbench.db.base import Base
from ragbench.db.session import get_engine
from ragbench.main import app


@pytest.mark.asyncio
async def test_experiment_creation_and_baseline_comparison():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Create Dataset
        ds_payload = {
            "name": "Experiment Test Dataset",
            "version": "1.0.0",
            "items": [
                {
                    "query": "What is company revenue?",
                    "expected_output": "Mock response to: What is company revenue?",
                    "contexts": ["Revenue reached $10M."]
                }
            ]
        }
        ds_res = await client.post("/api/v1/datasets", json=ds_payload)
        assert ds_res.status_code == 201
        dataset_id = ds_res.json()["id"]

        # 2. Run Baseline Experiment
        exp1_payload = {
            "name": "Baseline Experiment v1",
            "dataset_id": dataset_id,
            "provider_name": "mock",
            "model_name": "mock-model-v1"
        }
        exp1_res = await client.post("/api/v1/experiments", json=exp1_payload)
        assert exp1_res.status_code == 201
        exp1_id = exp1_res.json()["id"]

        # 3. Set Baseline
        base_res = await client.post(f"/api/v1/experiments/{exp1_id}/set-baseline")
        assert base_res.status_code == 200
        assert base_res.json()["is_baseline"] is True

        # 4. Run Candidate Experiment
        exp2_payload = {
            "name": "Candidate Experiment v2",
            "dataset_id": dataset_id,
            "provider_name": "mock",
            "model_name": "mock-model-v2"
        }
        exp2_res = await client.post("/api/v1/experiments", json=exp2_payload)
        assert exp2_res.status_code == 201
        exp2_id = exp2_res.json()["id"]

        # 5. Compare Candidate vs Baseline
        cmp_res = await client.get(f"/api/v1/experiments/{exp2_id}/compare")
        assert cmp_res.status_code == 200
        cmp_data = cmp_res.json()
        assert cmp_data["candidate_name"] == "Candidate Experiment v2"
        assert "exact_match" in cmp_data["metric_deltas"]
