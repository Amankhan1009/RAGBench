"""Factory for instantiating LLM provider implementations."""
from typing import Dict, Type

from ragbench.providers.base import BaseLLMProvider
from ragbench.providers.groq import GroqProvider
from ragbench.providers.mock import MockLLMProvider


class ProviderFactory:
    """Registry and factory manager for LLM providers."""
    _registry: Dict[str, Type[BaseLLMProvider]] = {
        "mock": MockLLMProvider,
        "groq": GroqProvider,
    }

    @classmethod
    def register_provider(cls, name: str, provider_cls: Type[BaseLLMProvider]) -> None:
        """Register a new LLM provider class."""
        cls._registry[name.lower()] = provider_cls

    @classmethod
    def create(cls, provider_name: str, api_key: str, model: str) -> BaseLLMProvider:
        """Instantiate a provider instance by name."""
        name_key = provider_name.lower()
        if name_key not in cls._registry:
            raise ValueError(
                f"Unsupported LLM provider '{provider_name}'. Supported providers: {list(cls._registry.keys())}"
            )
        provider_cls = cls._registry[name_key]
        return provider_cls(api_key=api_key, model=model)
