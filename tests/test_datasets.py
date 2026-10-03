"""Integration test suite for Dataset REST endpoints."""
import pytest
from httpx import ASGITransport, AsyncClient

import ragbench.models
from ragbench.db.base import Base
from ragbench.db.session import get_engine
from ragbench.main import app


@pytest.mark.asyncio
async def test_dataset_creation_and_retrieval():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Create Dataset
        payload = {
            "name": "RAG Q&A Benchmark",
            "description": "Baseline evaluation dataset for financial QA",
            "version": "1.0.0",
            "items": [
                {
                    "query": "What is the net revenue?",
                    "expected_output": "$10 Million",
                    "contexts": ["Revenue reached $10M in Q4."],
                    "item_metadata": {"category": "finance"}
                }
            ]
        }
        res = await client.post("/api/v1/datasets", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "RAG Q&A Benchmark"
        assert len(data["items"]) == 1
        dataset_id = data["id"]

        # 2. Bulk Add Items
        bulk_payload = [
            {
                "query": "What was EBITDA?",
                "expected_output": "$2.5 Million",
                "contexts": ["EBITDA was $2.5M."],
                "item_metadata": {"category": "finance"}
            }
        ]
        add_res = await client.post(f"/api/v1/datasets/{dataset_id}/items", json=bulk_payload)
        assert add_res.status_code == 201
        assert len(add_res.json()) == 1

        # 3. Retrieve Dataset
        get_res = await client.get(f"/api/v1/datasets/{dataset_id}")
        assert get_res.status_code == 200
        dataset_data = get_res.json()
        assert len(dataset_data["items"]) == 2
