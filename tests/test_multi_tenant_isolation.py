"""Comprehensive multi-tenant session and workspace isolation verification suite for RAGBench v2.0."""
import pytest
from httpx import ASGITransport, AsyncClient

import ragbench.models
from ragbench.db.base import Base
from ragbench.db.session import get_engine
from ragbench.main import app


@pytest.mark.asyncio
async def test_complete_multi_tenant_workspace_isolation():
    """Verify that User A and User B operate in 100% isolated sessions with zero cross-tenant leakage."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Register User A (Alice)
        reg_a = await client.post(
            "/api/v1/auth/register",
            json={"email": "alice@company-a.com", "password": "Password123!", "name": "Alice"}
        )
        assert reg_a.status_code == 201
        token_a = reg_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # 2. Register User B (Bob)
        reg_b = await client.post(
            "/api/v1/auth/register",
            json={"email": "bob@enterprise-b.com", "password": "SecurePassword456!", "name": "Bob"}
        )
        assert reg_b.status_code == 201
        token_b = reg_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # 3. User A creates a dataset
        ds_a_res = await client.post(
            "/api/v1/datasets",
            headers=headers_a,
            json={
                "name": "Alice Confidential Dataset",
                "version": "1.0.0",
                "items": [
                    {
                        "query": "What is Q3 operating margin?",
                        "expected_output": "24.5%",
                        "contexts": ["Q3 operating margin reached 24.5%."],
                    }
                ]
            }
        )
        assert ds_a_res.status_code == 201
        ds_a = ds_a_res.json()
        ds_a_id = ds_a["id"]

        # 4. User B lists datasets -> MUST BE EMPTY (0 datasets for User B)
        list_b = await client.get("/api/v1/datasets", headers=headers_b)
        assert list_b.status_code == 200
        assert len(list_b.json()) == 0, "User B should not see User A's datasets"

        # 5. User B tries to GET User A's dataset by ID -> MUST RETURN 404
        get_b = await client.get(f"/api/v1/datasets/{ds_a_id}", headers=headers_b)
        assert get_b.status_code == 404, "User B must not be able to read User A's dataset"

        # 6. User B tries to bulk add items to User A's dataset -> MUST RETURN 404
        hack_items = await client.post(
            f"/api/v1/datasets/{ds_a_id}/items",
            headers=headers_b,
            json=[{"query": "Injected query", "contexts": ["Injected context"]}]
        )
        assert hack_items.status_code == 404, "User B must not be able to modify User A's dataset"

        # 7. User B tries to run an experiment targeting User A's dataset -> MUST RETURN 404
        hack_exp = await client.post(
            "/api/v1/experiments",
            headers=headers_b,
            json={
                "name": "Bob unauthorized run",
                "dataset_id": ds_a_id,
                "provider_name": "mock",
                "model_name": "mock-model"
            }
        )
        assert hack_exp.status_code == 404, "User B must not be able to run experiments on User A's dataset"

        # 8. User A runs an experiment and sets it as baseline
        exp_a_res = await client.post(
            "/api/v1/experiments",
            headers=headers_a,
            json={
                "name": "Alice Baseline Run v1",
                "dataset_id": ds_a_id,
                "provider_name": "mock",
                "model_name": "mock-model"
            }
        )
        assert exp_a_res.status_code == 201
        exp_a_id = exp_a_res.json()["id"]

        set_base_a = await client.post(f"/api/v1/experiments/{exp_a_id}/set-baseline", headers=headers_a)
        assert set_base_a.status_code == 200
        assert set_base_a.json()["is_baseline"] is True

        # 9. User B lists experiments -> MUST BE EMPTY (0 experiments for User B)
        exp_list_b = await client.get("/api/v1/experiments", headers=headers_b)
        assert exp_list_b.status_code == 200
        assert len(exp_list_b.json()) == 0, "User B must not see User A's experiments"

        # 10. User B tries to check regression on User A's experiment -> MUST RETURN 404
        hack_ci = await client.get(f"/api/v1/experiments/{exp_a_id}/check-regression", headers=headers_b)
        assert hack_ci.status_code == 404, "User B must not access User A's regression reports"

        # 11. User B tries to delete User A's experiment or dataset -> MUST RETURN 404
        hack_del_exp = await client.delete(f"/api/v1/experiments/{exp_a_id}", headers=headers_b)
        assert hack_del_exp.status_code == 404

        hack_del_ds = await client.delete(f"/api/v1/datasets/{ds_a_id}", headers=headers_b)
        assert hack_del_ds.status_code == 404

        # 12. User B creates their own isolated dataset & experiment
        ds_b_res = await client.post(
            "/api/v1/datasets",
            headers=headers_b,
            json={
                "name": "Bob Public QA Suite",
                "version": "1.0.0",
                "items": [{"query": "What is AI?", "expected_output": "Artificial Intelligence"}]
            }
        )
        assert ds_b_res.status_code == 201
        ds_b_id = ds_b_res.json()["id"]

        # User A lists datasets -> sees ONLY Alice's dataset, NOT Bob's!
        list_a = await client.get("/api/v1/datasets", headers=headers_a)
        assert list_a.status_code == 200
        assert len(list_a.json()) == 1
        assert list_a.json()[0]["id"] == ds_a_id

        # User B lists datasets -> sees ONLY Bob's dataset, NOT Alice's!
        list_b_final = await client.get("/api/v1/datasets", headers=headers_b)
        assert list_b_final.status_code == 200
        assert len(list_b_final.json()) == 1
        assert list_b_final.json()[0]["id"] == ds_b_id

        # 13. User A deletes their own dataset -> 204 No Content
        del_a = await client.delete(f"/api/v1/datasets/{ds_a_id}", headers=headers_a)
        assert del_a.status_code == 204

        list_a_after = await client.get("/api/v1/datasets", headers=headers_a)
        assert len(list_a_after.json()) == 0
