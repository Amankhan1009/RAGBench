"""Unit and Integration tests for Regression Detector & CI Endpoint."""
import pytest
from httpx import ASGITransport, AsyncClient
from ragbench.db.base import Base
from ragbench.db.session import get_engine
from ragbench.evaluators.regression import RegressionDetector
from ragbench.main import app
import ragbench.models


def test_regression_detector_pass_and_fail():
    detector = RegressionDetector(tolerance=0.02)

    cand_pass = {"exact_match": 0.95, "hit_rate": 1.0}
    base_pass = {"exact_match": 0.90, "hit_rate": 1.0}
    report_pass = detector.detect_regression(cand_pass, base_pass)
    assert report_pass.has_regression is False
    assert len(report_pass.regressed_metrics) == 0

    cand_fail = {"exact_match": 0.80, "hit_rate": 1.0}
    base_fail = {"exact_match": 0.90, "hit_rate": 1.0}
    report_fail = detector.detect_regression(cand_fail, base_fail)
    assert report_fail.has_regression is True
    assert "exact_match" in report_fail.regressed_metrics


@pytest.mark.asyncio
async def test_regression_api_endpoint():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        ds_res = await client.post("/api/v1/datasets", json={
            "name": "Regression Test Dataset",
            "items": [{"query": "Q1", "expected_output": "Mock response to: Q1"}]
        })
        ds_id = ds_res.json()["id"]

        exp1_res = await client.post("/api/v1/experiments", json={
            "name": "Baseline Exp",
            "dataset_id": ds_id,
            "provider_name": "mock"
        })
        exp1_id = exp1_res.json()["id"]
        await client.post(f"/api/v1/experiments/{exp1_id}/set-baseline")

        exp2_res = await client.post("/api/v1/experiments", json={
            "name": "Candidate Exp",
            "dataset_id": ds_id,
            "provider_name": "mock"
        })
        exp2_id = exp2_res.json()["id"]

        reg_res = await client.get(f"/api/v1/experiments/{exp2_id}/check-regression?tolerance=0.02")
        assert reg_res.status_code == 200
        data = reg_res.json()
        assert data["has_regression"] is False
