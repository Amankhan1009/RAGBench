"""Tests for LangSmith tracing, secret redaction, and zero-leakage payload sanitization."""
import pytest
from ragbench.core.tracing import (
    TraceManager,
    redact_text,
    sanitize_payload,
    trace_async_run,
    trace_manager,
)


def test_redact_secrets_in_strings():
    groq_secret = "Using key gsk_1234567890abcdef1234567890 for API calls"
    openai_secret = "Authorization: sk-abcdef1234567890abcdef1234567890"
    anthropic_secret = "Token sk-ant-abcdef1234567890abcdef1234567890"
    google_secret = f"Key AIza{'X' * 35}"
    bearer_secret = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secret"

    assert "gsk_" not in redact_text(groq_secret)
    assert "[REDACTED_SECRET]" in redact_text(groq_secret)

    assert "sk-" not in redact_text(openai_secret)
    assert "[REDACTED_SECRET]" in redact_text(openai_secret)

    assert "sk-ant-" not in redact_text(anthropic_secret)
    assert "[REDACTED_SECRET]" in redact_text(anthropic_secret)

    assert "AIza" not in redact_text(google_secret)
    assert "[REDACTED_SECRET]" in redact_text(google_secret)

    assert "eyJhbGci" not in redact_text(bearer_secret)
    assert "[REDACTED_SECRET]" in redact_text(bearer_secret)


def test_sanitize_payload_dictionary_and_lists():
    payload = {
        "api_key": "raw_sensitive_key_value",
        "model": "openai/gpt-oss-120b",
        "nested": {
            "token": "secret_token_123",
            "prompt": "Here is gsk_1234567890abcdef1234567890 prompt text",
        },
        "items": [
            {"authorization": "Bearer token1234567890abcdef12345"},
            "Plain text prompt with sk-1234567890abcdef1234567890",
        ],
    }

    sanitized = sanitize_payload(payload)

    assert sanitized["api_key"] == "[REDACTED_SECRET]"
    assert sanitized["model"] == "openai/gpt-oss-120b"
    assert sanitized["nested"]["token"] == "[REDACTED_SECRET]"
    assert "gsk_" not in sanitized["nested"]["prompt"]
    assert "[REDACTED_SECRET]" in sanitized["nested"]["prompt"]
    assert sanitized["items"][0]["authorization"] == "[REDACTED_SECRET]"
    assert "sk-" not in sanitized["items"][1]
    assert "[REDACTED_SECRET]" in sanitized["items"][1]


@pytest.mark.asyncio
async def test_trace_async_run_context_manager():
    trace_manager.clear()

    inputs = {"prompt": "Summarize RAGBench", "api_key": "gsk_1234567890abcdef1234567890"}
    metadata = {"provider": "groq", "secret": "super_secret_value"}

    async with trace_async_run("test_llm_call", run_type="llm", inputs=inputs, metadata=metadata) as outputs:
        outputs["completion"] = "RAGBench is an evaluation platform."

    spans = trace_manager.traces
    assert len(spans) == 1
    span = spans[0]

    assert span.name == "test_llm_call"
    assert span.run_type == "llm"
    assert span.latency_ms >= 0.0
    assert span.error is None

    # Verify zero secret leakage
    assert span.inputs["api_key"] == "[REDACTED_SECRET]"
    assert span.inputs["prompt"] == "Summarize RAGBench"
    assert span.metadata["secret"] == "[REDACTED_SECRET]"
    assert span.outputs["completion"] == "RAGBench is an evaluation platform."


@pytest.mark.asyncio
async def test_trace_async_run_error_handling():
    trace_manager.clear()

    with pytest.raises(RuntimeError):
        async with trace_async_run("failing_call", run_type="evaluator", inputs={"query": "test"}):
            raise RuntimeError("API failed with key gsk_1234567890abcdef1234567890")

    spans = trace_manager.traces
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "failing_call"
    assert span.error is not None
    assert "gsk_" not in span.error
    assert "[REDACTED_SECRET]" in span.error

def test_logging_scrubs_secrets(caplog):
    import logging
    from ragbench.core.logging import logger

    with caplog.at_level(logging.INFO):
        logger.info("Initializing Groq client with key gsk_1234567890abcdef1234567890")

    assert "gsk_" not in caplog.text
    assert "[REDACTED_SECRET]" in caplog.text