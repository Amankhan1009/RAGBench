"""Abstract base class and response schemas for LLM providers."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ProviderResponse(BaseModel):
    """Standardized response schema across all LLM providers."""
    generated_text: str = Field(description="The primary model output text")
    prompt_tokens: int = Field(default=0, description="Input token count")
    completion_tokens: int = Field(default=0, description="Output token count")
    total_tokens: int = Field(default=0, description="Total tokens consumed")
    latency_ms: float = Field(default=0.0, description="Execution duration in milliseconds")
    cost_usd: float = Field(default=0.0, description="Calculated USD cost")
    model_name: str = Field(description="Model identifier (e.g. llama-3.3-70b-versatile)")
    provider_name: str = Field(description="Provider name (e.g. Groq, OpenAI, Anthropic, Google)")
    raw_response: Optional[Dict[str, Any]] = Field(default=None, description="Raw provider metadata")


class BaseLLMProvider(ABC):
    """Unified interface that all LLM providers must implement."""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 1000
    ) -> ProviderResponse:
        """Generate text completion from prompt."""
        pass

    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        temperature: float = 0.0,
        max_tokens: int = 1000
    ) -> ProviderResponse:
        """Generate structured JSON completion adhering to schema."""
        pass
