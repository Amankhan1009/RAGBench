"""Unit tests for Groq Provider implementation using mocked HTTP calls."""
import pytest

from ragbench.providers.factory import ProviderFactory
from ragbench.providers.groq import GroqProvider


@pytest.mark.asyncio
async def test_groq_provider_mocked_generate(httpx_mock):
    httpx_mock.add_response(
        url=GroqProvider.GROQ_API_URL,
        json={
            "choices": [{"message": {"content": "Groq benchmark output"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25}
        }
    )

    provider = ProviderFactory.create("groq", api_key="gsk_fake_key", model="openai/gpt-oss-120b")
    assert isinstance(provider, GroqProvider)

    response = await provider.generate("Test prompt")
    assert response.generated_text == "Groq benchmark output"
    assert response.prompt_tokens == 10
    assert response.completion_tokens == 15
    assert response.provider_name == "Groq"
    assert response.model_name == "openai/gpt-oss-120b"
