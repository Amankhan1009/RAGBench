"""Mock LLM provider implementation for deterministic testing."""
import json
import time
from typing import Any, Dict
from ragbench.providers.base import BaseLLMProvider, ProviderResponse


class MockLLMProvider(BaseLLMProvider):
    """Deterministic mock provider for unit tests and local benchmarking."""

    def __init__(self, api_key: str = "mock-key", model: str = "mock-model"):
        super().__init__(api_key=api_key, model=model)

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 1000
    ) -> ProviderResponse:
        start_time = time.perf_counter()
        output_text = f"Mock response to: {prompt}"
        latency = (time.perf_counter() - start_time) * 1000.0

        return ProviderResponse(
            generated_text=output_text,
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(output_text.split()),
            total_tokens=len(prompt.split()) + len(output_text.split()),
            latency_ms=round(latency, 2),
            cost_usd=0.00001,
            model_name=self.model,
            provider_name="Mock",
            raw_response={"mock": True}
        )

    async def generate_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        temperature: float = 0.0,
        max_tokens: int = 1000
    ) -> ProviderResponse:
        start_time = time.perf_counter()
        json_output = json.dumps({"score": 1.0, "reasoning": "Mock evaluation pass"})
        latency = (time.perf_counter() - start_time) * 1000.0

        return ProviderResponse(
            generated_text=json_output,
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(json_output.split()),
            total_tokens=len(prompt.split()) + len(json_output.split()),
            latency_ms=round(latency, 2),
            cost_usd=0.00001,
            model_name=self.model,
            provider_name="Mock",
            raw_response={"mock_json": True}
        )
