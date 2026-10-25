"""Integration test suite for Dataset Ingestion (CSV/JSONL) & Executive Reports (Phase 20)."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

import ragbench.models  # noqa: F401
from ragbench.db.base import Base
from ragbench.db.session import get_engine
from ragbench.main import app

SAMPLE_CSV = """query,expected_output,contexts,category
"What is the maximum return window?","Customers can return items within 30 days of delivery.","['Delivery receipt confirms the 30-day return eligibility window.']","returns"
"Are expedited shipping fees refundable?","No, expedited shipping fees are non-refundable once dispatched.","['Standard priority express shipping surcharges cannot be credited back.']","shipping"
"How can I track my international shipment?","Tracking numbers are sent via encrypted email upon carrier dispatch.","['Encrypted tracking codes are dispatched automatically via email.']","tracking"
"""

SAMPLE_CUSTOM_CSV = """user_prompt;gold_target;retrieved_chunks;department
"How do I reset my API key?";"Visit the BYOK settings tab.";"API keys are managed under workspace settings.";"support"
"Can I invite team members?";"Yes, in organization settings.";"Multi-user collaboration is available on pro tier.";"admin"
"""

SAMPLE_JSONL = """{"query": "What is the return policy?", "expected_output": "30 days window", "contexts": ["Returns accepted within 30 days."]}
{"query": "Where is the tracking number?", "expected_output": "Sent via email", "contexts": ["Dispatched via email notification."]}
"""


@pytest.fixture(autouse=True)
async def setup_test_db():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.mark.asyncio
async def test_ingest_csv_auto_detection():
    """Verify CSV dataset is ingested with auto-detected columns."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Register user
        unique_email = f"user_{uuid.uuid4().hex[:8]}@test.com"
        reg = await client.post(
            "/api/v1/auth/register",
            json={"email": unique_email, "password": "password123", "name": "Ingest User"},
        )
        assert reg.status_code == 201
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        res = await client.post(
            "/api/v1/datasets/ingest",
            headers=headers,
            json={
                "name": "Shipping Ingested QA",
                "description": "Imported from CSV",
                "file_format": "csv",
                "content": SAMPLE_CSV,
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["total_ingested"] == 3
        assert data["skipped_rows"] == 0
        assert data["dataset"]["name"] == "Shipping Ingested QA"
        assert len(data["dataset"]["items"]) == 3
        assert data["dataset"]["items"][0]["query"] == "What is the maximum return window?"
        assert data["dataset"]["items"][0]["expected_output"] == "Customers can return items within 30 days of delivery."


@pytest.mark.asyncio
async def test_ingest_csv_custom_mapping():
    """Verify CSV dataset is ingested with custom column mapping and delimiter."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        unique_email = f"user_{uuid.uuid4().hex[:8]}@test.com"
        reg = await client.post(
            "/api/v1/auth/register",
            json={"email": unique_email, "password": "password123", "name": "Custom User"},
        )
        assert reg.status_code == 201
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        res = await client.post(
            "/api/v1/datasets/ingest",
            headers=headers,
            json={
                "name": "Custom Department QA",
                "file_format": "csv",
                "content": SAMPLE_CUSTOM_CSV,
                "column_mapping": {
                    "query": "user_prompt",
                    "expected_output": "gold_target",
                    "contexts": "retrieved_chunks",
                },
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["total_ingested"] == 2
        assert len(data["dataset"]["items"]) == 2
        assert data["dataset"]["items"][0]["query"] == "How do I reset my API key?"


@pytest.mark.asyncio
async def test_ingest_jsonl():
    """Verify JSONL dataset is ingested and parsed line-by-line."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        unique_email = f"user_{uuid.uuid4().hex[:8]}@test.com"
        reg = await client.post(
            "/api/v1/auth/register",
            json={"email": unique_email, "password": "password123", "name": "JSONL User"},
        )
        assert reg.status_code == 201
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        res = await client.post(
            "/api/v1/datasets/ingest",
            headers=headers,
            json={
                "name": "JSONL Benchmark Suite",
                "file_format": "jsonl",
                "content": SAMPLE_JSONL,
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["total_ingested"] == 2
        assert len(data["dataset"]["items"]) == 2


@pytest.mark.asyncio
async def test_ingest_empty_rejection():
    """Verify empty or headerless file is rejected with HTTP 400."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        unique_email = f"user_{uuid.uuid4().hex[:8]}@test.com"
        reg = await client.post(
            "/api/v1/auth/register",
            json={"email": unique_email, "password": "password123", "name": "Empty User"},
        )
        assert reg.status_code == 201
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        res = await client.post(
            "/api/v1/datasets/ingest",
            headers=headers,
            json={
                "name": "Empty Dataset",
                "file_format": "csv",
                "content": "   \n\n  ",
            },
        )
        assert res.status_code == 400
        assert "No valid evaluation items" in res.json()["detail"]


@pytest.mark.asyncio
async def test_export_markdown_csv_and_jsonl():
    """Verify experiment exports in Markdown, CSV, and JSONL formats."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        unique_email = f"user_{uuid.uuid4().hex[:8]}@test.com"
        reg = await client.post(
            "/api/v1/auth/register",
            json={"email": unique_email, "password": "password123", "name": "Export User"},
        )
        assert reg.status_code == 201
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Ingest dataset
        ingest_res = await client.post(
            "/api/v1/datasets/ingest",
            headers=headers,
            json={
                "name": "Export Benchmark",
                "file_format": "csv",
                "content": SAMPLE_CSV,
            },
        )
        assert ingest_res.status_code == 201
        dataset_id = ingest_res.json()["dataset"]["id"]

        # 2. Run experiment
        exp_res = await client.post(
            "/api/v1/experiments",
            headers=headers,
            json={
                "name": "Export Target Run",
                "dataset_id": dataset_id,
                "provider_name": "mock",
                "model_name": "mock-model",
                "api_key": "mock-key",
            },
        )
        assert exp_res.status_code == 201
        exp_id = exp_res.json()["id"]

        # 3. Export Markdown
        md_res = await client.get(f"/api/v1/experiments/{exp_id}/export/markdown", headers=headers)
        assert md_res.status_code == 200
        assert "text/markdown" in md_res.headers["content-type"]
        md_text = md_res.text
        assert "# 📊 RAGBench Executive Evaluation Report" in md_text
        assert "Export Target Run" in md_text
        assert "What is the maximum return window?" in md_text

        # 4. Export CSV
        csv_res = await client.get(f"/api/v1/experiments/{exp_id}/export/csv", headers=headers)
        assert csv_res.status_code == 200
        assert "text/csv" in csv_res.headers["content-type"]
        assert "attachment" in csv_res.headers["content-disposition"]
        csv_text = csv_res.text
        assert "sample_id,experiment_id,query,response" in csv_text
        assert "What is the maximum return window?" in csv_text

        # 5. Export JSONL
        jsonl_res = await client.get(f"/api/v1/experiments/{exp_id}/export/jsonl", headers=headers)
        assert jsonl_res.status_code == 200
        assert "application/x-ndjson" in jsonl_res.headers["content-type"]
        assert "attachment" in jsonl_res.headers["content-disposition"]
        jsonl_text = jsonl_res.text
        assert "sample_id" in jsonl_text
        assert "What is the maximum return window?" in jsonl_text


@pytest.mark.asyncio
async def test_export_tenant_isolation():
    """Verify User B cannot export User A's experiment records."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # User A
        reg_a = await client.post(
            "/api/v1/auth/register",
            json={"email": f"tenant_a_{uuid.uuid4().hex[:8]}@test.com", "password": "password123", "name": "User A"},
        )
        assert reg_a.status_code == 201
        token_a = reg_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        ds_res = await client.post(
            "/api/v1/datasets/ingest",
            headers=headers_a,
            json={"name": "A Dataset", "file_format": "csv", "content": SAMPLE_CSV},
        )
        ds_id = ds_res.json()["dataset"]["id"]

        exp_res = await client.post(
            "/api/v1/experiments",
            headers=headers_a,
            json={
                "name": "A Experiment",
                "dataset_id": ds_id,
                "provider_name": "mock",
                "api_key": "mock-key",
            },
        )
        exp_id = exp_res.json()["id"]

        # User B
        reg_b = await client.post(
            "/api/v1/auth/register",
            json={"email": f"tenant_b_{uuid.uuid4().hex[:8]}@test.com", "password": "password123", "name": "User B"},
        )
        assert reg_b.status_code == 201
        token_b = reg_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User B attempts to export User A's experiment -> HTTP 404
        for export_fmt in ["markdown", "csv", "jsonl"]:
            res = await client.get(f"/api/v1/experiments/{exp_id}/export/{export_fmt}", headers=headers_b)
            assert res.status_code == 404
