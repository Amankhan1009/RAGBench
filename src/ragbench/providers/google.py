"""Model-independent Google Gemini LLM provider implementation."""
import json
import time
from typing import Any, Dict
import httpx
from ragbench.providers.base import BaseLLMProvider, ProviderResponse, calculate_token_cost


class GoogleProvider(BaseLLMProvider):
    """Google Gemini API implementation supporting ANY model identifier."""

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 1000
    ) -> ProviderResponse:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }

        start_time = time.perf_counter()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                raise RuntimeError(
                    f"Google API call failed [{response.status_code}]: {response.text}"
                )
            data = response.json()

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        output_text = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        completion_tokens = usage.get("candidatesTokenCount", 0)
        total_tokens = usage.get("totalTokenCount", prompt_tokens + completion_tokens)
        cost_usd = calculate_token_cost(prompt_tokens, completion_tokens, self.input_cost_per_1k, self.output_cost_per_1k)

        return ProviderResponse(
            generated_text=output_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=round(latency_ms, 2),
            cost_usd=cost_usd,
            model_name=self.model,
            provider_name="Google",
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
