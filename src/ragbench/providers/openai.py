"""Model-independent OpenAI LLM provider implementation."""
import json
import time
from typing import Any, Dict
import httpx
from ragbench.providers.base import BaseLLMProvider, ProviderResponse, estimate_token_cost


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API implementation supporting ANY model string (gpt-4o, o3-mini, o1, etc.)."""

    OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str, model: str):
        super().__init__(api_key=api_key, model=model)

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 1000
    ) -> ProviderResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
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
            response = await client.post(self.OPENAI_API_URL, headers=headers, json=payload)
            if response.status_code != 200:
                raise RuntimeError(
                    f"OpenAI API call failed [{response.status_code}]: {response.text}"
                )
            data = response.json()

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        output_text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
        cost_usd = estimate_token_cost(self.model, prompt_tokens, completion_tokens)

        return ProviderResponse(
            generated_text=output_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=round(latency_ms, 2),
            cost_usd=cost_usd,
            model_name=self.model,
            provider_name="OpenAI",
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
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": formatted_prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"}
        }

        start_time = time.perf_counter()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.OPENAI_API_URL, headers=headers, json=payload)
            if response.status_code != 200:
                raise RuntimeError(
                    f"OpenAI JSON API call failed [{response.status_code}]: {response.text}"
                )
            data = response.json()

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        output_text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
        cost_usd = estimate_token_cost(self.model, prompt_tokens, completion_tokens)

        return ProviderResponse(
            generated_text=output_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=round(latency_ms, 2),
            cost_usd=cost_usd,
            model_name=self.model,
            provider_name="OpenAI",
            raw_response=data
        )
