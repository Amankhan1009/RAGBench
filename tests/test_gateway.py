"""Unit and integration tests for AI Gateway, Semantic Cache, Resilient Routing, and Budgets."""
import uuid

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from ragbench.db.base import Base
from ragbench.db.session import get_engine
from ragbench.gateway.budget import BudgetManager
from ragbench.gateway.cache import SemanticCache
from ragbench.gateway.router import GatewayRouter
from ragbench.main import app


@pytest.fixture(autouse=True)
async def setup_test_db():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture
def clean_cache():
    """Isolated SemanticCache instance for test isolation."""
    return SemanticCache(default_ttl_seconds=3600)


@pytest.fixture
def clean_budget():
    """Isolated BudgetManager instance for test isolation."""
    return BudgetManager()



# ==========================================
# 1. SEMANTIC & EXACT CACHE UNIT TESTS
# ==========================================

def test_exact_cache_hit_and_miss(clean_cache):
    ws_id = "test-ws-1"
    prompt = "What is Retrieval-Augmented Generation?"
    model = "mock-model"

    # Initial lookup must miss
    miss = clean_cache.get(ws_id, prompt, model)
    assert miss is None

    # Populate cache
    key = clean_cache.set(
        workspace_id=ws_id,
        prompt=prompt,
        model=model,
        response_text="RAG combines search retrieval with generative LLMs.",
        prompt_tokens=8,
        completion_tokens=9,
        cost_usd=0.00005,
        latency_ms=120.0,
        provider_name="Mock",
    )
    assert key is not None

    # Lookup must hit
    hit_result = clean_cache.get(ws_id, prompt, model)
    assert hit_result is not None
    entry, match_type = hit_result
    assert match_type == "exact"
    assert entry.response_text == "RAG combines search retrieval with generative LLMs."
    assert entry.hit_count == 1

    # Verify stats
    stats = clean_cache.get_stats(ws_id)
    assert stats.total_requests == 2
    assert stats.cache_hits == 1
    assert stats.cache_misses == 1
    assert stats.hit_rate == 0.5
    assert stats.total_cost_saved_usd == 0.00005


def test_semantic_cache_hit(clean_cache):
    ws_id = "test-ws-semantic"
    prompt_original = "What are the benefits of regular physical exercise for health?"
    prompt_similar = "What are the benefits of regular physical exercise for human health?"
    model = "mock-model"

    clean_cache.set(
        workspace_id=ws_id,
        prompt=prompt_original,
        model=model,
        response_text="Exercise improves cardiovascular health and mental wellbeing.",
        prompt_tokens=10,
        completion_tokens=8,
        cost_usd=0.00004,
        latency_ms=85.0,
        provider_name="Mock",
    )

    # Similar query lookup with threshold=0.8
    result = clean_cache.get(ws_id, prompt_similar, model, similarity_threshold=0.8)
    assert result is not None
    entry, match_type = result
    assert "semantic" in match_type
    assert entry.response_text == "Exercise improves cardiovascular health and mental wellbeing."


def test_cache_ttl_expiration(clean_cache):
    ws_id = "test-ws-ttl"
    prompt = "Expiring prompt query"
    model = "mock-model"

    # Set with 0-second TTL
    clean_cache.set(
        workspace_id=ws_id,
        prompt=prompt,
        model=model,
        response_text="Should expire instantly",
        prompt_tokens=3,
        completion_tokens=3,
        cost_usd=0.00001,
        latency_ms=10.0,
        provider_name="Mock",
        ttl_seconds=-1,
    )

    result = clean_cache.get(ws_id, prompt, model)
    assert result is None


def test_multi_tenant_cache_isolation(clean_cache):
    ws_a = "tenant-alpha"
    ws_b = "tenant-bravo"
    prompt = "Confidential financial projection"
    model = "mock-model"

    clean_cache.set(
        workspace_id=ws_a,
        prompt=prompt,
        model=model,
        response_text="Alpha revenue is $10M",
        prompt_tokens=4,
        completion_tokens=5,
        cost_usd=0.00002,
        latency_ms=50.0,
        provider_name="Mock",
    )

    # Tenant Bravo must not access Tenant Alpha's cached output
    assert clean_cache.get(ws_b, prompt, model) is None

    # Tenant Alpha accesses normally
    res_a = clean_cache.get(ws_a, prompt, model)
    assert res_a is not None
    assert res_a[0].response_text == "Alpha revenue is $10M"


def test_cache_purge(clean_cache):
    ws_id = "test-ws-purge"
    clean_cache.set(
        workspace_id=ws_id,
        prompt="Query 1",
        model="mock",
        response_text="Resp 1",
        prompt_tokens=2,
        completion_tokens=2,
        cost_usd=0.00001,
        latency_ms=10.0,
        provider_name="Mock",
    )
    clean_cache.set(
        workspace_id=ws_id,
        prompt="Query 2",
        model="mock",
        response_text="Resp 2",
        prompt_tokens=2,
        completion_tokens=2,
        cost_usd=0.00001,
        latency_ms=10.0,
        provider_name="Mock",
    )

    assert clean_cache.get_stats(ws_id).cached_entries_count == 2
    cleared = clean_cache.purge(ws_id)
    assert cleared == 2
    assert clean_cache.get_stats(ws_id).cached_entries_count == 0


# ==========================================
# 2. BUDGET MANAGER UNIT TESTS
# ==========================================

def test_budget_manager_spending_cap(clean_budget):
    ws_id = "test-budget-ws"

    # Set budget of $0.05
    clean_budget.set_limits(ws_id, monthly_budget_usd=0.05, monthly_token_quota=10000)

    # Initial check passes
    clean_budget.check_budget(ws_id)

    # Record spend below limit
    clean_budget.record_usage(ws_id, cost_usd=0.03, tokens=2000)
    clean_budget.check_budget(ws_id)

    status = clean_budget.get_status(ws_id)
    assert status.current_month_cost_usd == 0.03
    assert status.cost_usage_percentage == 60.0
    assert status.budget_exceeded is False

    # Record spend exceeding limit
    clean_budget.record_usage(ws_id, cost_usd=0.03, tokens=3000)
    assert clean_budget.get_status(ws_id).budget_exceeded is True

    # Check budget must now raise HTTP 429
    with pytest.raises(HTTPException) as exc_info:
        clean_budget.check_budget(ws_id)
    assert exc_info.value.status_code == 429
    assert "budget limit" in exc_info.value.detail


def test_budget_manager_token_quota(clean_budget):
    ws_id = "test-token-ws"
    clean_budget.set_limits(ws_id, monthly_budget_usd=None, monthly_token_quota=5000)

    clean_budget.record_usage(ws_id, cost_usd=0.01, tokens=6000)
    with pytest.raises(HTTPException) as exc_info:
        clean_budget.check_budget(ws_id)
    assert exc_info.value.status_code == 429
    assert "token quota" in exc_info.value.detail


# ==========================================
# 3. ROUTER INFERENCE TESTS
# ==========================================

def test_router_provider_inference():
    router = GatewayRouter()
    assert router.infer_provider("openai/gpt-oss-120b") == "groq"
    assert router.infer_provider("llama-3.3-70b-versatile") == "groq"
    assert router.infer_provider("gpt-4o-mini") == "openai"
    assert router.infer_provider("claude-3-5-sonnet") == "anthropic"
    assert router.infer_provider("gemini-1.5-flash") == "google"
    assert router.infer_provider("https://api.mycompany.com/rag") == "webhook"
    assert router.infer_provider("any-model", explicit_provider="mock") == "mock"


# ==========================================
# 4. FULL API ENDPOINT INTEGRATION TESTS
# ==========================================

@pytest.mark.asyncio
async def test_gateway_chat_completions_caching_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register user and acquire JWT token
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"gateway_caching_{uuid.uuid4().hex[:6]}@test.com",
                "password": "password123",
                "name": "Gateway Cache User",
            },
        )
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "model": "mock-model",
            "messages": [{"role": "user", "content": "What is AI Gateway?"}],
            "provider": "mock",
            "cache_enabled": True,
        }

        # 1. First Call: Cache Miss -> Live Mock Generation
        res1 = await client.post("/api/v1/gateway/chat/completions", json=payload, headers=headers)
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["object"] == "chat.completion"
        assert len(data1["choices"]) == 1
        assert "Mock response to:" in data1["choices"][0]["message"]["content"]
        assert data1["gateway"]["cached"] is False
        assert data1["gateway"]["provider_used"] == "mock"

        # 2. Second Call with identical query: Cache Hit (<5ms, cost $0.00)
        res2 = await client.post("/api/v1/gateway/chat/completions", json=payload, headers=headers)
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["gateway"]["cached"] is True
        assert data2["gateway"]["cost_usd"] == 0.0
        assert data2["choices"][0]["message"]["content"] == data1["choices"][0]["message"]["content"]

        # 3. Third Call with cache_enabled=False: Bypass Cache
        payload_bypass = dict(payload, cache_enabled=False)
        res3 = await client.post("/api/v1/gateway/chat/completions", json=payload_bypass, headers=headers)
        assert res3.status_code == 200
        assert res3.json()["gateway"]["cached"] is False

        # 4. Check Gateway Stats Endpoint
        res_stats = await client.get("/api/v1/gateway/stats", headers=headers)
        assert res_stats.status_code == 200
        stats = res_stats.json()
        assert stats["total_requests"] >= 2
        assert stats["cache_hits"] >= 1

        # 5. Purge Cache Endpoint
        res_purge = await client.post("/api/v1/gateway/cache/purge", headers=headers)
        assert res_purge.status_code == 200
        assert res_purge.json()["status"] == "success"


@pytest.mark.asyncio
async def test_gateway_budget_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"budget_api_{uuid.uuid4().hex[:6]}@test.com",
                "password": "password123",
                "name": "Budget User",
            },
        )
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # GET budget status
        res = await client.get("/api/v1/gateway/budget", headers=headers)
        assert res.status_code == 200
        assert "workspace_id" in res.json()

        # POST update budget limits
        update_payload = {"monthly_budget_usd": 150.0, "monthly_token_quota": 500000}
        res_update = await client.post("/api/v1/gateway/budget", json=update_payload, headers=headers)
        assert res_update.status_code == 200
        data = res_update.json()
        assert data["monthly_budget_usd"] == 150.0
        assert data["monthly_token_quota"] == 500000


@pytest.mark.asyncio
async def test_gateway_automated_failover():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"failover_api_{uuid.uuid4().hex[:6]}@test.com",
                "password": "password123",
                "name": "Failover User",
            },
        )
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Request with primary provider 'google' (no key in vault), but with fallback 'mock'
        payload = {
            "model": "gemini-1.5-flash",
            "messages": [{"role": "user", "content": "Test failover resiliency"}],
            "provider": "google",
            "fallback_providers": ["mock"],
            "cache_enabled": False,
        }

        res = await client.post("/api/v1/gateway/chat/completions", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()
        # Primary 'google' had no key or failed, so it automatically failed over to 'mock'!
        assert data["gateway"]["fallback_triggered"] is True
        assert data["gateway"]["provider_used"] == "mock"
        assert "mock" in data["gateway"]["attempted_providers"]

        assert data["gateway"]["provider_used"] == "mock"
        assert "mock" in data["gateway"]["attempted_providers"]
