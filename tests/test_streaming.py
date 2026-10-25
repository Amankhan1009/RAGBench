"""Tests for Server-Sent Events (SSE) live evaluation streaming."""
import json
import uuid

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
async def test_stream_experiment_validation():
    """Verify stream endpoint validates dataset existence and permissions."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={"email": f"stream_val_{uuid.uuid4().hex[:6]}@test.com", "password": "password123", "name": "Stream User"},
        )
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Non-existent dataset
        res = await client.post(
            "/api/v1/experiments/stream",
            headers=headers,
            json={
                "name": "Invalid Stream",
                "dataset_id": str(uuid.uuid4()),
                "provider_name": "mock",
                "model_name": "mock-model",
            },
        )
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_stream_experiment_sse_events():
    """Verify SSE streaming yields started, sample_completed, and completed events."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={"email": f"stream_run_{uuid.uuid4().hex[:6]}@test.com", "password": "password123", "name": "Stream Run"},
        )
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create dataset with 2 items
        ds_res = await client.post(
            "/api/v1/datasets",
            headers=headers,
            json={
                "name": "Stream Test Dataset",
                "version": "1.0.0",
                "items": [
                    {"query": "Sample question 1?", "expected_output": "Answer 1", "contexts": ["Context 1"]},
                    {"query": "Sample question 2?", "expected_output": "Answer 2", "contexts": ["Context 2"]},
                ],
            },
        )
        assert ds_res.status_code == 201
        dataset_id = ds_res.json()["id"]

        # 2. Call streaming endpoint
        stream_res = await client.post(
            "/api/v1/experiments/stream",
            headers=headers,
            json={
                "name": "Live Streaming Test",
                "dataset_id": dataset_id,
                "provider_name": "mock",
                "model_name": "mock-model",
            },
        )
        assert stream_res.status_code == 200
        assert "text/event-stream" in stream_res.headers["content-type"]

        # Parse SSE events from response text
        content = stream_res.text
        blocks = [b.strip() for b in content.split("\n\n") if b.strip()]

        events_received = []
        for block in blocks:
            lines = block.split("\n")
            event_type = None
            data_str = None
            for line in lines:
                if line.startswith("event:"):
                    event_type = line.replace("event:", "").strip()
                elif line.startswith("data:"):
                    data_str = line.replace("data:", "").strip()
            if event_type and data_str:
                events_received.append((event_type, json.loads(data_str)))

        # Assert correct event sequence
        assert len(events_received) >= 4  # started, sample 1, sample 2, completed
        event_names = [e[0] for e in events_received]
        assert event_names[0] == "started"
        assert event_names[1] == "sample_completed"
        assert event_names[2] == "sample_completed"
        assert event_names[3] == "completed"

        # Verify started event payload
        started_payload = events_received[0][1]
        assert started_payload["total_samples"] == 2
        assert started_payload["provider_name"] == "mock"

        # Verify sample_completed payloads
        sample_1 = events_received[1][1]
        assert sample_1["sample_index"] == 1
        assert sample_1["progress_pct"] == 50.0

        sample_2 = events_received[2][1]
        assert sample_2["sample_index"] == 2
        assert sample_2["progress_pct"] == 100.0

        # Verify completed payload
        completed_payload = events_received[3][1]
        assert completed_payload["status"] == "SUCCESS"
        assert completed_payload["total_samples"] == 2
        assert completed_payload["successful_samples"] == 2
        assert completed_payload["failed_samples"] == 0


@pytest.mark.asyncio
async def test_stream_workspace_isolation():
    """Verify User B cannot initiate a streaming evaluation on User A's dataset."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User A
        u_a = await client.post(
            "/api/v1/auth/register",
            json={"email": f"stream_a_{uuid.uuid4().hex[:6]}@test.com", "password": "password123", "name": "User A"},
        )
        token_a = u_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        ds_a = await client.post(
            "/api/v1/datasets",
            headers=headers_a,
            json={
                "name": "User A Dataset",
                "version": "1.0.0",
                "items": [{"query": "Private query?", "expected_output": "Private answer"}],
            },
        )
        ds_a_id = ds_a.json()["id"]

        # User B
        u_b = await client.post(
            "/api/v1/auth/register",
            json={"email": f"stream_b_{uuid.uuid4().hex[:6]}@test.com", "password": "password123", "name": "User B"},
        )
        token_b = u_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User B tries to stream evaluation on User A's dataset
        res = await client.post(
            "/api/v1/experiments/stream",
            headers=headers_b,
            json={
                "name": "Unauthorized Stream",
                "dataset_id": ds_a_id,
                "provider_name": "mock",
                "model_name": "mock-model",
            },
        )
        assert res.status_code == 404
