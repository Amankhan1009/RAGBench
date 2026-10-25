"""Integration test suite for Synthetic AI Test Dataset Generator (Phase 19)."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

import ragbench.models  # noqa: F401
from ragbench.db.base import Base
from ragbench.db.session import get_engine
from ragbench.main import app

SAMPLE_POLICY = """RAGBench Global Shipping and Return Policy (v2.4)

1. Delivery Timelines & Tracking
Standard ground shipping orders are processed within 1 to 2 business days. Delivery across North America typically takes between 3 to 5 business days. Express overnight priority shipping is available for all orders placed before 2:00 PM EST.

2. Return Window & Eligibility Requirements
Customers may initiate a full refund return within 30 days of confirmed delivery receipt. To be eligible for a full credit refund, items must remain in their original unworn condition.

3. Restocking Fees & Return Shipping Labels
Standard customer-initiated returns are subject to a nominal $4.50 restocking and inspection surcharge, which will be automatically deducted from the final refund credit balance. Defective items receive full fee waivers."""


@pytest.mark.asyncio
async def test_generate_synthetic_validation():
    """Verify short text under 50 chars fails schema validation with HTTP 422."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            "/api/v1/datasets/generate-synthetic",
            json={
                "raw_text": "Too short",
                "num_samples": 3,
                "provider_name": "mock",
            },
        )
        assert res.status_code == 422


@pytest.mark.asyncio
async def test_generate_synthetic_mock():
    """Verify mock provider generates structured test items across difficulty modes."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            "/api/v1/datasets/generate-synthetic",
            json={
                "raw_text": SAMPLE_POLICY,
                "num_samples": 3,
                "difficulty": "mixed",
                "provider_name": "mock",
                "model_name": "mock-model",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total_generated"] == 3
        assert data["provider_used"] == "mock"
        assert len(data["items"]) == 3

        # Verify items have expected fields
        for item in data["items"]:
            assert "query" in item and len(item["query"]) > 5
            assert "expected_output" in item and len(item["expected_output"]) > 5
            assert "contexts" in item and len(item["contexts"]) > 0
            assert item["difficulty"] in ["factual", "reasoning", "adversarial"]


@pytest.mark.asyncio
async def test_generate_synthetic_and_save_dataset():
    """Verify synthesized items can be persisted directly as a new benchmark dataset."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Synthesize
        gen_res = await client.post(
            "/api/v1/datasets/generate-synthetic",
            json={
                "raw_text": SAMPLE_POLICY,
                "num_samples": 2,
                "difficulty": "factual",
                "provider_name": "mock",
            },
        )
        assert gen_res.status_code == 200
        gen_data = gen_res.json()
        items = gen_data["items"]

        # 2. Save as Dataset
        create_payload = {
            "name": "Synthesized Policy QA",
            "description": "Benchmark created via AI generator",
            "version": "1.0.0",
            "items": [
                {
                    "query": it["query"],
                    "expected_output": it["expected_output"],
                    "contexts": it["contexts"],
                    "item_metadata": {
                        "difficulty": it["difficulty"],
                        "synthesized_by": "mock",
                    },
                }
                for it in items
            ],
        }
        ds_res = await client.post("/api/v1/datasets", json=create_payload)
        assert ds_res.status_code == 201
        ds_data = ds_res.json()
        assert ds_data["name"] == "Synthesized Policy QA"
        assert len(ds_data["items"]) == 2
        assert ds_data["items"][0]["contexts"] is not None


@pytest.mark.asyncio
async def test_generate_synthetic_missing_api_key():
    """Verify calling an unconfigured cloud provider without a BYOK key yields HTTP 400."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            "/api/v1/datasets/generate-synthetic",
            json={
                "raw_text": SAMPLE_POLICY,
                "num_samples": 2,
                "provider_name": "anthropic",
            },
        )
        # Should reject because Anthropic has no key configured
        assert res.status_code == 400
        assert "No API key configured" in res.json()["detail"]


@pytest.mark.asyncio
async def test_synthetic_dataset_tenant_isolation():
    """Verify datasets created from synthetic generator respect multi-tenant workspace boundaries."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Register User A
        reg_a = await client.post(
            "/api/v1/auth/register",
            json={"email": f"synth_a_{uuid.uuid4().hex[:8]}@test.com", "password": "password123", "name": "User A"},
        )
        assert reg_a.status_code == 201
        token_a = reg_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # User A generates synthetic items and creates dataset
        gen_res = await client.post(
            "/api/v1/datasets/generate-synthetic",
            headers=headers_a,
            json={
                "raw_text": SAMPLE_POLICY,
                "num_samples": 2,
                "difficulty": "factual",
                "provider_name": "mock",
            },
        )
        assert gen_res.status_code == 200
        items = gen_res.json()["items"]

        ds_res = await client.post(
            "/api/v1/datasets",
            headers=headers_a,
            json={
                "name": "User A Private Benchmark",
                "version": "1.0.0",
                "items": [
                    {
                        "query": items[0]["query"],
                        "expected_output": items[0]["expected_output"],
                        "contexts": items[0]["contexts"],
                    }
                ],
            },
        )
        assert ds_res.status_code == 201
        ds_id = ds_res.json()["id"]

        # Register User B
        reg_b = await client.post(
            "/api/v1/auth/register",
            json={"email": f"synth_b_{uuid.uuid4().hex[:8]}@test.com", "password": "password123", "name": "User B"},
        )
        assert reg_b.status_code == 201
        token_b = reg_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User B lists datasets -> should NOT contain User A's dataset
        b_list = await client.get("/api/v1/datasets", headers=headers_b)
        assert b_list.status_code == 200
        b_ids = [d["id"] for d in b_list.json()]
        assert ds_id not in b_ids

        # User B directly queries User A's dataset -> HTTP 404
        b_get = await client.get(f"/api/v1/datasets/{ds_id}", headers=headers_b)
        assert b_get.status_code == 404
