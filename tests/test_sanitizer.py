"""Comprehensive test suite for Phase 25: Automated PII Masking & Data Sanitization Pipeline."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from ragbench.main import app
from ragbench.sanitizer.engine import pii_sanitizer
from ragbench.sanitizer.schemas import (
    MaskingStrategy,
    PIIEntityType,
    PIISanitizerConfig,
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
        unique_email = f"sanitizer_{uuid.uuid4().hex[:8]}@example.com"
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={"email": unique_email, "password": "securepassword123", "name": "Sanitizer Tester"}
        )
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}


# ==========================================
# 1. Detection Unit Tests
# ==========================================

def test_detect_email():
    """Detect standard, dotted, and subaddressed email addresses."""
    text = "Please reach out to support@acme.com or john.doe+billing@domain.org for help."
    matches = pii_sanitizer.detect_entities(text)
    emails = [m for m in matches if m.entity_type == PIIEntityType.EMAIL]
    assert len(emails) == 2
    assert emails[0].text == "support@acme.com"
    assert emails[1].text == "john.doe+billing@domain.org"


def test_detect_ssn():
    """Detect valid US Social Security Numbers and ignore invalid patterns."""
    text = "Candidate SSN is 123-45-6789. Ref code: 000-12-3456 (invalid area)."
    matches = pii_sanitizer.detect_entities(text)
    ssns = [m for m in matches if m.entity_type == PIIEntityType.SSN]
    assert len(ssns) == 1
    assert ssns[0].text == "123-45-6789"


def test_detect_credit_card_luhn_verification():
    """Detect valid credit cards via Luhn checksum while rejecting non-card numbers."""
    # Valid Visa test number (4532 0150 1234 5671 passes Luhn)
    valid_card = "4532-0150-1234-5671"
    # Invalid card number (fails Luhn)
    invalid_card = "1234-5678-9012-3456"

    text = f"Charged card {valid_card} and tracked order {invalid_card}."
    matches = pii_sanitizer.detect_entities(text)
    cards = [m for m in matches if m.entity_type == PIIEntityType.CREDIT_CARD]
    assert len(cards) == 1
    assert cards[0].text == valid_card


def test_detect_phone():
    """Detect US and international phone formats."""
    text = "Call me at +1-415-555-2671 or (800) 555-0199 for dispatch."
    matches = pii_sanitizer.detect_entities(text)
    phones = [m for m in matches if m.entity_type == PIIEntityType.PHONE_NUMBER]
    assert len(phones) >= 2


def test_detect_api_keys_and_secrets():
    """Detect OpenAI, AWS, and generic secret tokens."""
    text = (
        "OpenAI key: sk-live9876543210abcdef12345678, "
        "AWS root: AKIAIOSFODNN7EXAMPLE."
    )
    matches = pii_sanitizer.detect_entities(text)
    api_keys = [m for m in matches if m.entity_type == PIIEntityType.API_KEY]
    assert len(api_keys) == 2


def test_detect_ip_address():
    """Detect IPv4 addresses."""
    text = "Gateway routing through 192.168.1.105 and DNS 8.8.8.8."
    matches = pii_sanitizer.detect_entities(text)
    ips = [m for m in matches if m.entity_type == PIIEntityType.IP_ADDRESS]
    assert len(ips) == 2


# ==========================================
# 2. Masking Strategies & Reversible Unmasking
# ==========================================

def test_masking_strategy_token_and_reversible_restore():
    """Token strategy must generate [ENTITY_N] tokens and enable exact rehydration."""
    raw = "User alice@example.com called from 415-555-1234 with SSN 123-45-6789."
    result = pii_sanitizer.sanitize(raw, PIISanitizerConfig(strategy=MaskingStrategy.TOKEN))

    assert "[EMAIL_1]" in result.sanitized_text
    assert "[PHONE_NUMBER_1]" in result.sanitized_text
    assert "[SSN_1]" in result.sanitized_text
    assert "alice@example.com" not in result.sanitized_text
    assert "123-45-6789" not in result.sanitized_text

    # Reversible unmasking
    restored = pii_sanitizer.restore(result.sanitized_text, result.token_map)
    assert restored.restored_text == raw
    assert restored.tokens_restored_count == 3


def test_masking_strategy_redact():
    """Redact strategy should use generic [REDACTED_TYPE] tags."""
    raw = "Send receipt to bob@company.com."
    result = pii_sanitizer.sanitize(raw, PIISanitizerConfig(strategy=MaskingStrategy.REDACT))
    assert result.sanitized_text == "Send receipt to [REDACTED_EMAIL]."


def test_masking_strategy_hash():
    """Hash strategy must append a deterministic 6-character hex hash."""
    raw = "Send receipt to bob@company.com."
    result = pii_sanitizer.sanitize(raw, PIISanitizerConfig(strategy=MaskingStrategy.HASH))
    assert "[EMAIL_" in result.sanitized_text
    assert len(result.entities_found) == 1


# ==========================================
# 3. RAG PII Leakage Evaluator
# ==========================================

def test_evaluate_leakage_detected():
    """Should flag when confidential context PII appears unmasked in output."""
    context = ["Patient Jane Doe: SSN 987-65-4321, Phone 206-555-0144."]
    output = "Patient's SSN is 987-65-4321 and contact is 206-555-0144."

    audit = pii_sanitizer.evaluate_leakage(context, output)
    assert audit.leaked is True
    assert audit.total_leaked_count == 2
    assert audit.leakage_score == 1.0
    assert "ALERT" in audit.reason


def test_evaluate_leakage_safe():
    """Should confirm safe when output contains zero context PII or only masked tokens."""
    context = ["Patient Jane Doe: SSN 987-65-4321, Phone 206-555-0144."]
    output = "The patient intake form has been received and verified under HIPAA compliance."

    audit = pii_sanitizer.evaluate_leakage(context, output)
    assert audit.leaked is False
    assert audit.total_leaked_count == 0
    assert audit.leakage_score == 0.0


# ==========================================
# 4. REST API Integration Tests
# ==========================================

@pytest.mark.asyncio
async def test_api_mask_and_unmask_endpoints(auth_headers):
    """POST /api/v1/sanitizer/mask and /unmask roundtrip."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Mask
        mask_res = await client.post(
            "/api/v1/sanitizer/mask",
            headers=auth_headers,
            json={"text": "Contact ceo@startup.io at 650-555-1122."},
        )
        assert mask_res.status_code == 200
        mask_data = mask_res.json()
        assert "[EMAIL_1]" in mask_data["sanitized_text"]
        token_map = mask_data["token_map"]

        # 2. Unmask
        unmask_res = await client.post(
            "/api/v1/sanitizer/unmask",
            headers=auth_headers,
            json={
                "sanitized_text": mask_data["sanitized_text"],
                "token_map": token_map,
            },
        )
        assert unmask_res.status_code == 200
        unmask_data = unmask_res.json()
        assert unmask_data["restored_text"] == "Contact ceo@startup.io at 650-555-1122."
        assert unmask_data["tokens_restored_count"] == 2


@pytest.mark.asyncio
async def test_api_detect_and_presets_endpoints(auth_headers):
    """POST /api/v1/sanitizer/detect and GET /presets."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Detect
        detect_res = await client.post(
            "/api/v1/sanitizer/detect",
            headers=auth_headers,
            json={"text": "My AWS key is AKIAIOSFODNN7EXAMPLE."},
        )
        assert detect_res.status_code == 200
        matches = detect_res.json()
        assert len(matches) == 1
        assert matches[0]["entity_type"] == "api_key"

        # Presets
        presets_res = await client.get("/api/v1/sanitizer/presets")
        assert presets_res.status_code == 200
        presets = presets_res.json()
        assert len(presets) >= 3


# ==========================================
# 5. AI Gateway PII Masking E2E
# ==========================================

@pytest.mark.asyncio
async def test_gateway_pii_sanitization_e2e(auth_headers):
    """Gateway must mask prompt PII, serve generation, and record PII metadata."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "model": "mock-model",
            "messages": [
                {"role": "user", "content": "Please verify user alice@test.org with phone 415-555-9012."}
            ],
            "pii_sanitization_enabled": True,
            "pii_restore_response": True,
            "cache_enabled": False,
        }
        res = await client.post("/api/v1/gateway/chat/completions", headers=auth_headers, json=payload)
        assert res.status_code == 200
        data = res.json()

        # Gateway diagnostic metadata assertions
        gw = data["gateway"]
        assert gw["pii_sanitized"] is True
        assert gw["pii_entities_masked_count"] == 2
        assert "email" in gw["pii_entities_detected"]
        assert "phone_number" in gw["pii_entities_detected"]
        assert gw["pii_latency_ms"] >= 0.0
