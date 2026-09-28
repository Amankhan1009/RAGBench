"""Model-independent Anthropic LLM provider implementation."""
import json
import time
from typing import Any, Dict
import httpx
from ragbench.providers.base import BaseLLMProvider, ProviderResponse, estimate_token_cost


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude implementation supporting ANY model string (claude-3-7-sonnet, etc.)."""

    ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str, model: str):
        super().__init__(api_key=api_key, model=model)

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 1000
    ) -> ProviderResponse:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        start_time = time.perf_counter()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.ANTHROPIC_API_URL, headers=headers, json=payload)
            if response.status_code != 200:
                raise RuntimeError(
                    f"Anthropic API call failed [{response.status_code}]: {response.text}"
                )
            data = response.json()

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        output_text = data["content"][0]["text"]
        usage = data.get("usage", {})
        prompt_tokens = usage.get("input_tokens", 0)
        completion_tokens = usage.get("output_tokens", 0)
        total_tokens = prompt_tokens + completion_tokens
        cost_usd = estimate_token_cost(self.model, prompt_tokens, completion_tokens)

        return ProviderResponse(
            generated_text=output_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=round(latency_ms, 2),
            cost_usd=cost_usd,
            model_name=self.model,
            provider_name="Anthropic",
            raw_response=data
        )

    async def generate_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        temperature: float = 0.0,
        max_tokens: int = 1000
    ) -> ProviderResponse:
        formatted_prompt = f"{prompt}\nReturn strict JSON matching this schema: {json.dumps(schema)}"
        return await self.generate(formatted_prompt, temperature=temperature, max_tokens=max_tokens)
