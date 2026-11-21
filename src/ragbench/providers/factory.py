"""Factory for instantiating LLM provider implementations."""
import inspect
from typing import Any, Dict, Type

from ragbench.providers.base import BaseLLMProvider
from ragbench.providers.groq import GroqProvider
from ragbench.providers.mock import MockLLMProvider
from ragbench.providers.webhook import WebhookProvider


class ProviderFactory:
    """Registry and factory manager for LLM providers."""
    _registry: Dict[str, Type[BaseLLMProvider]] = {
        "mock": MockLLMProvider,
        "groq": GroqProvider,
        "webhook": WebhookProvider,
        "custom": WebhookProvider,
    }

    @classmethod
    def register_provider(cls, name: str, provider_cls: Type[BaseLLMProvider]) -> None:
        """Register a new LLM provider class."""
        cls._registry[name.lower()] = provider_cls

    @classmethod
    def create(
        cls,
        provider_name: str,
        api_key: str,
        model: str,
        **kwargs: Any,
    ) -> BaseLLMProvider:
        """Instantiate a provider instance by name, forwarding supported kwargs."""
        name_key = provider_name.lower()
        if name_key not in cls._registry:
            raise ValueError(
                f"Unsupported LLM provider '{provider_name}'. Supported providers: {list(cls._registry.keys())}"
            )
        provider_cls = cls._registry[name_key]

        # Filter kwargs to only those accepted by provider_cls.__init__
        sig = inspect.signature(provider_cls.__init__)
        supported_kwargs = {}
        for k, v in kwargs.items():
            if k in sig.parameters and v is not None:
                supported_kwargs[k] = v

        return provider_cls(api_key=api_key, model=model, **supported_kwargs)

