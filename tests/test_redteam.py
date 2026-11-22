"""Comprehensive test suite for Phase 26: AI Red-Teaming & Adversarial Benchmark Suite."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from ragbench.main import app
from ragbench.redteam.attacks import ATTACK_CATALOG, get_attack_catalog
from ragbench.redteam.engine import redteam_engine
from ragbench.redteam.schemas import (
    AttackCategory,
    AttackResultStatus,
    RedTeamBenchmarkRequest,
)


@pytest.fixture(autouse=True)
async def setup_test_db():
    from ragbench.db.base import Base
    from ragbench.db.session import get_engine
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture
async def auth_headers():
    """Register fresh test user and return authentication headers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_email = f"redteam_{uuid.uuid4().hex[:8]}@example.com"
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={"email": unique_email, "password": "securepassword123", "name": "RedTeam Tester"}
        )
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}


# ==========================================
# 1. Attack Catalog Unit Tests
# ==========================================

def test_attack_catalog_completeness():
    """Verify attack catalog contains comprehensive attacks across all 6 categories."""
    attacks = get_attack_catalog()
    assert len(attacks) >= 20

    # Ensure all 6 categories are represented
    categories_present = {a.category for a in attacks}
    assert AttackCategory.DIRECT_INJECTION in categories_present
    assert AttackCategory.JAILBREAK in categories_present
    assert AttackCategory.INDIRECT_INJECTION in categories_present
    assert AttackCategory.SYSTEM_EXTRACTION in categories_present
    assert AttackCategory.TOPICAL_EVASION in categories_present
    assert AttackCategory.PII_LEAKAGE in categories_present

    # Validate schema fields on each attack
    for a in attacks:
        assert a.id
        assert a.name
        assert a.prompt
        assert a.severity
        assert a.mitigation_recommendation


def test_attack_catalog_category_filtering():
    """Verify category filtering works correctly."""
    filtered = get_attack_catalog([AttackCategory.JAILBREAK])
    assert len(filtered) >= 4
    assert all(a.category == AttackCategory.JAILBREAK for a in filtered)


# ==========================================
# 2. Attack Execution Unit Tests
# ==========================================

@pytest.mark.asyncio
async def test_attack_defended_by_guardrails():
    """Direct prompt injection should be intercepted pre-execution by guardrails with $0 cost."""
    override_attack = next(a for a in ATTACK_CATALOG if a.id == "dpi_universal_override")
    ws_id = "test-redteam-ws"

    res = await redteam_engine.execute_attack(
        workspace_id=ws_id,
        test_case=override_attack,
        provider_name="mock",
        model="mock-model",
        guardrails_enabled=True,
    )

    assert res.status == AttackResultStatus.DEFENDED
    assert res.guardrails_intercepted is True
    assert res.cost_usd == 0.0
    assert "security policies" in res.model_output.lower()


@pytest.mark.asyncio
async def test_attack_pii_leakage_sanitization():
    """PII leakage attack should have context sanitized when pii_sanitization_enabled=True."""
    pii_attack = next(a for a in ATTACK_CATALOG if a.id == "pel_customer_ssn_dox")
    ws_id = "test-redteam-ws"

    res = await redteam_engine.execute_attack(
        workspace_id=ws_id,
        test_case=pii_attack,
        provider_name="mock",
        model="mock-model",
        guardrails_enabled=False,
        pii_sanitization_enabled=True,
    )

    # When PII is sanitized, raw SSN (123-45-6789) is not in context
    assert res.status == AttackResultStatus.DEFENDED


# ==========================================
# 3. Full Benchmark Suite Tests
# ==========================================

@pytest.mark.asyncio
async def test_run_benchmark_mock_provider():
    """Run full benchmark against mock provider and verify posture scoring."""
    ws_id = "test-redteam-suite"
    req = RedTeamBenchmarkRequest(
        provider="mock",
        model="mock-model",
        categories=[AttackCategory.DIRECT_INJECTION, AttackCategory.JAILBREAK],
        guardrails_enabled=True,
    )

    report = await redteam_engine.run_benchmark(ws_id, req)

    assert report.total_attacks >= 8
    assert report.defended_attacks >= 0
    assert 0.0 <= report.security_posture_score <= 100.0
    assert report.risk_grade
    assert AttackCategory.DIRECT_INJECTION.value in report.defense_rate_by_category
    assert AttackCategory.JAILBREAK.value in report.defense_rate_by_category
    assert len(report.attack_results) == report.total_attacks

    # Verify report is stored
    reports = redteam_engine.get_reports(ws_id)
    assert len(reports) >= 1
    assert reports[0].benchmark_id == report.benchmark_id


# ==========================================
# 4. REST API Endpoints Integration Tests
# ==========================================

@pytest.mark.asyncio
async def test_api_attacks_catalog_endpoint():
    """GET /api/v1/redteam/attacks should return catalog."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # All attacks
        res = await client.get("/api/v1/redteam/attacks")
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 20

        # Filtered by category
        res_cat = await client.get("/api/v1/redteam/attacks?category=jailbreak")
        assert res_cat.status_code == 200
        cat_data = res_cat.json()
        assert len(cat_data) >= 4
        assert all(a["category"] == "jailbreak" for a in cat_data)


@pytest.mark.asyncio
async def test_api_run_benchmark_and_reports_crud(auth_headers):
    """POST /api/v1/redteam/run and GET /reports."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "provider": "mock",
            "model": "mock-model",
            "categories": ["system_extraction", "topical_evasion"],
            "guardrails_enabled": True,
            "pii_sanitization_enabled": True,
        }
        run_res = await client.post("/api/v1/redteam/run", headers=auth_headers, json=payload)
        assert run_res.status_code == 200
        report_data = run_res.json()

        assert "benchmark_id" in report_data
        assert report_data["total_attacks"] >= 8
        assert report_data["security_posture_score"] >= 0.0
        bench_id = report_data["benchmark_id"]

        # Fetch reports list
        list_res = await client.get("/api/v1/redteam/reports", headers=auth_headers)
        assert list_res.status_code == 200
        reports_list = list_res.json()
        assert len(reports_list) >= 1
        assert any(r["benchmark_id"] == bench_id for r in reports_list)

        # Fetch report details by ID
        detail_res = await client.get(f"/api/v1/redteam/reports/{bench_id}", headers=auth_headers)
        assert detail_res.status_code == 200
        detail_data = detail_res.json()
        assert detail_data["benchmark_id"] == bench_id
        assert len(detail_data["attack_results"]) == detail_data["total_attacks"]
