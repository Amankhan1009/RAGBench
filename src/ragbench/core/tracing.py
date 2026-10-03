"""LangSmith observability bridge and zero-leakage BYOK secret redactor."""
import contextlib
from datetime import datetime, timezone
import os
import re
import time
from typing import Any, Dict, List, Optional
import uuid
import httpx
from pydantic import BaseModel, Field

from ragbench.core.config import settings
from ragbench.core.logging import logger

# Regex patterns matching cloud provider API keys and sensitive tokens
SECRET_PATTERNS = [
    re.compile(r"gsk_[a-zA-Z0-9]{20,}", re.IGNORECASE),               # Groq
    re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE),                # OpenAI
    re.compile(r"sk-ant-[a-zA-Z0-9\-]{20,}", re.IGNORECASE),          # Anthropic
    re.compile(r"AIza[0-9A-Za-z\-_]{35}", re.IGNORECASE),             # Google API Key
    re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE),    # Bearer Tokens
    re.compile(r"([A-Za-z0-9+/]{42,44}={0,2})"),                      # Fernet Base64 Keys
]

SENSITIVE_KEY_NAMES = {
    "api_key",
    "apikey",
    "secret",
    "token",
    "authorization",
    "password",
    "encryption_key",
    "encrypted_key",
}


def redact_text(text: str) -> str:
    """Mask any detected API keys or security tokens in raw strings."""
    if not isinstance(text, str):
        return text
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED_SECRET]", redacted)
    return redacted


def sanitize_payload(obj: Any) -> Any:
    """
    Recursively sanitize dictionaries, lists, and primitives.
    Replaces sensitive dictionary keys and redacts secret values.
    """
    if isinstance(obj, dict):
        sanitized = {}
        for k, v in obj.items():
            if str(k).lower() in SENSITIVE_KEY_NAMES:
                sanitized[k] = "[REDACTED_SECRET]"
            else:
                sanitized[k] = sanitize_payload(v)
        return sanitized
    elif isinstance(obj, list):
        return [sanitize_payload(item) for item in obj]
    elif isinstance(obj, str):
        return redact_text(obj)
    return obj


class TraceSpan(BaseModel):
    """Normalized trace record for LLM provider or evaluator runs."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    run_type: str = Field(description="Run type: 'llm', 'evaluator', 'chain', or 'tool'")
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = 0.0
    error: Optional[str] = None
    created_at: float = Field(default_factory=time.time)


class TraceManager:
    """Manages active trace records with zero-leakage guarantees and LangSmith export."""

    def __init__(self):
        self._traces: List[TraceSpan] = []

    def clear(self):
        self._traces.clear()

    @property
    def traces(self) -> List[TraceSpan]:
        return list(self._traces)

    def record_span(
        self,
        name: str,
        run_type: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        latency_ms: float = 0.0,
        error: Optional[str] = None,
    ) -> TraceSpan:
        """Sanitize and record a completed execution span."""
        span = TraceSpan(
            name=name,
            run_type=run_type,
            inputs=sanitize_payload(inputs),
            outputs=sanitize_payload(outputs),
            metadata=sanitize_payload(metadata or {}),
            latency_ms=latency_ms,
            error=redact_text(error) if error else None,
        )
        self._traces.append(span)

        api_key = os.getenv("LANGCHAIN_API_KEY") or settings.LANGCHAIN_API_KEY
        tracing_on = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true" or settings.LANGCHAIN_TRACING_V2
        if tracing_on and api_key:
            self._export_to_langsmith(span, api_key)

        return span

    def _export_to_langsmith(self, span: TraceSpan, api_key: str):
        """Export sanitized trace directly to LangSmith Cloud API."""
        project = os.getenv("LANGCHAIN_PROJECT", "ragbench")
        endpoint = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")

        now_iso = datetime.now(timezone.utc).isoformat()
        payload = {
            "id": span.id,
            "name": span.name,
            "run_type": span.run_type if span.run_type in ["llm", "chain", "tool"] else "chain",
            "inputs": span.inputs,
            "outputs": span.outputs,
            "extra": {"metadata": span.metadata},
            "session_name": project,
            "start_time": now_iso,
            "end_time": now_iso,
            "error": span.error,
        }

        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.post(
                    f"{endpoint.rstrip('/')}/runs",
                    headers={"x-api-key": api_key, "Content-Type": "application/json"},
                    json=payload,
                )
                if res.status_code in [200, 201]:
                    logger.info(f"[LangSmith] Successfully exported trace: {span.name} (id={span.id})")
                else:
                    logger.warning(f"[LangSmith] Export rejected ({res.status_code}): {res.text}")
        except Exception as exc:
            logger.warning(f"[LangSmith] Could not connect to LangSmith API: {exc}")


trace_manager = TraceManager()


@contextlib.asynccontextmanager
async def trace_async_run(
    name: str,
    run_type: str = "llm",
    inputs: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    Async context manager to trace and benchmark operations.
    Guarantees secrets in inputs, outputs, and metadata are sanitized before recording.
    """
    start_time = time.perf_counter()
    outputs: Dict[str, Any] = {}
    error_msg: Optional[str] = None

    try:
        yield outputs
    except Exception as exc:
        error_msg = str(exc)
        raise
    finally:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        trace_manager.record_span(
            name=name,
            run_type=run_type,
            inputs=inputs or {},
            outputs=outputs,
            metadata=metadata or {},
            latency_ms=latency_ms,
            error=error_msg,
        )