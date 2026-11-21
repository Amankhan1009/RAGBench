"""Custom HTTP Webhook Provider for evaluating arbitrary external RAG services and LLM endpoints."""
import json
import time
from typing import Any, Dict, List, Optional

import httpx

from ragbench.providers.base import BaseLLMProvider, ProviderResponse, calculate_token_cost


class WebhookProvider(BaseLLMProvider):
    """Universal Webhook Provider for benchmarking any external RAG pipeline, FastAPI/Flask service,
    or proprietary LLM endpoint via HTTP POST / GET.

    Supports:
    - Custom URL endpoint (via `webhook_url` or `model`)
    - Configurable HTTP headers & Bearer tokens
    - Dot-notation JSON response extraction (e.g. 'answer', 'data.response', 'choices.0.message.content')
    - Context extraction for live RAG pipeline evaluations (e.g. 'contexts', 'retrieved_docs')
    - Fallback to raw string parsing for text/plain responses
    """

    DEFAULT_RESPONSE_KEYS = [
        "answer",
        "response",
        "output",
        "generated_text",
        "result",
        "text",
        "content",
        "message",
    ]

    DEFAULT_CONTEXTS_KEYS = [
        "contexts",
        "retrieved_contexts",
        "retrieved_docs",
        "documents",
        "sources",
        "chunks",
    ]

    def __init__(
        self,
        api_key: str = "",
        model: str = "",
        webhook_url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        response_path: str = "answer",
        contexts_path: Optional[str] = "contexts",
        http_method: str = "POST",
        timeout_seconds: float = 30.0,
        input_cost_per_1k: float = 0.0005,
        output_cost_per_1k: float = 0.0015,
    ):
        super().__init__(
            api_key=api_key,
            model=model,
            input_cost_per_1k=input_cost_per_1k,
            output_cost_per_1k=output_cost_per_1k,
        )
        self.webhook_url = webhook_url or model
        if not self.webhook_url:
            raise ValueError(
                "WebhookProvider requires a valid HTTP/HTTPS endpoint URL via 'webhook_url' or 'model'."
            )
        if not (self.webhook_url.startswith("http://") or self.webhook_url.startswith("https://")):
            raise ValueError(
                f"Invalid webhook URL '{self.webhook_url}'. Must begin with http:// or https://"
            )

        self.http_method = http_method.upper()
        self.timeout_seconds = timeout_seconds
        self.response_path = response_path or "answer"
        self.contexts_path = contexts_path or "contexts"

        # Initialize headers
        self.headers: Dict[str, str] = {"Content-Type": "application/json"}
        if headers:
            self.headers.update(headers)

        # Set Authorization header if api_key provided and not mock
        if api_key and api_key != "mock-key" and "Authorization" not in self.headers and "authorization" not in self.headers:
            self.headers["Authorization"] = f"Bearer {api_key}"

    @classmethod
    def extract_path(cls, data: Any, path: str) -> Any:
        """Traverse a dictionary or list using dot-notation path (e.g. 'choices.0.message.content')."""
        if not path or data is None:
            return None
        parts = path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    return None
            elif isinstance(current, list):
                try:
                    idx = int(part)
                    if 0 <= idx < len(current):
                        current = current[idx]
                    else:
                        return None
                except ValueError:
                    return None
            else:
                return None
        return current

    def _extract_response_text(self, data: Any) -> str:
        """Extract generated answer string from structured response data."""
        if isinstance(data, str):
            return data

        # Try user-specified path
        val = self.extract_path(data, self.response_path)
        if val is not None and isinstance(val, (str, int, float, bool)):
            return str(val)

        # Try default candidate keys
        if isinstance(data, dict):
            for candidate in self.DEFAULT_RESPONSE_KEYS:
                val = self.extract_path(data, candidate)
                if val is not None and isinstance(val, (str, int, float, bool)):
                    return str(val)

        # Fallback string representation
        if isinstance(data, dict):
            return json.dumps(data)
        return str(data)

    def _extract_contexts(self, data: Any) -> List[str]:
        """Extract retrieved context chunks from structured response data if present."""
        if not isinstance(data, dict):
            return []

        # Try user-specified contexts path
        val = self.extract_path(data, self.contexts_path)
        if isinstance(val, list):
            return [str(c) if not isinstance(c, dict) else c.get("text", c.get("content", str(c))) for c in val]

        # Try default candidate keys
        for candidate in self.DEFAULT_CONTEXTS_KEYS:
            val = self.extract_path(data, candidate)
            if isinstance(val, list):
                return [str(c) if not isinstance(c, dict) else c.get("text", c.get("content", str(c))) for c in val]

        return []

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ) -> ProviderResponse:
        """Execute HTTP request to external webhook and standardize response."""
        payload = {
            "query": prompt,
            "prompt": prompt,
            "question": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        start_time = time.perf_counter()
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                if self.http_method == "GET":
                    response = await client.get(
                        self.webhook_url,
                        headers=self.headers,
                        params={"query": prompt},
                    )
                else:
                    response = await client.post(
                        self.webhook_url,
                        headers=self.headers,
                        json=payload,
                    )
            except httpx.TimeoutException:
                raise RuntimeError(
                    f"Webhook request timed out after {self.timeout_seconds}s for URL: {self.webhook_url}"
                )
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to connect to webhook URL '{self.webhook_url}': {str(exc)}"
                )

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        if response.status_code >= 400:
            raise RuntimeError(
                f"Webhook call returned HTTP {response.status_code}: {response.text[:300]}"
            )

        # Parse response body
        raw_json: Optional[Any] = None
        retrieved_contexts: List[str] = []
        try:
            raw_json = response.json()
            generated_text = self._extract_response_text(raw_json)
            retrieved_contexts = self._extract_contexts(raw_json)
        except Exception:
            generated_text = response.text

        prompt_tokens = len(prompt.split())
        completion_tokens = len(generated_text.split())
        total_tokens = prompt_tokens + completion_tokens
        cost_usd = calculate_token_cost(
            prompt_tokens,
            completion_tokens,
            self.input_cost_per_1k,
            self.output_cost_per_1k,
        )

        return ProviderResponse(
            generated_text=generated_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=round(latency_ms, 2),
            cost_usd=cost_usd,
            model_name=self.webhook_url,
            provider_name="Webhook",
            raw_response={
                "data": raw_json if raw_json is not None else response.text,
                "retrieved_contexts": retrieved_contexts,
                "status_code": response.status_code,
            },
        )

    async def generate_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ) -> ProviderResponse:
        """Execute HTTP request expecting structured JSON adherence."""
        response = await self.generate(prompt=prompt, temperature=temperature, max_tokens=max_tokens)
        try:
            # Validate output is parseable JSON
            json.loads(response.generated_text)
        except Exception:
            # Wrap as JSON if raw string returned
            wrapped = json.dumps({"output": response.generated_text})
            response.generated_text = wrapped
        return response
