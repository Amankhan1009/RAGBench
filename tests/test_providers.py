"""Unit tests for Provider Abstraction Layer & Mock Provider."""
import pytest
from ragbench.providers.factory import ProviderFactory
from ragbench.providers.mock import MockLLMProvider


@pytest.mark.asyncio
async def test_mock_provider_generate():
    provider = ProviderFactory.create("mock", api_key="test-key", model="mock-v1")
    assert isinstance(provider, MockLLMProvider)

    response = await provider.generate("Evaluate context relevance")
    assert "Mock response" in response.generated_text
    assert response.provider_name == "Mock"
    assert response.model_name == "mock-v1"
    assert response.prompt_tokens > 0
    assert response.completion_tokens > 0


@pytest.mark.asyncio
async def test_mock_provider_generate_json():
    provider = ProviderFactory.create("mock", api_key="test-key", model="mock-v1")
    schema = {"type": "object", "properties": {"score": {"type": "number"}}}

    response = await provider.generate_json("Return evaluation score", schema=schema)
    assert "score" in response.generated_text
    assert response.cost_usd > 0.0


def test_unsupported_provider():
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        ProviderFactory.create("unknown_provider", api_key="key", model="model")
