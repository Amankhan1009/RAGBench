"""Abstract base class, pure token cost calculator, and response schemas for LLM providers."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


def calculate_token_cost(
    prompt_tokens: int,
    completion_tokens: int,
    input_cost_per_1k: float = 0.0005,
    output_cost_per_1k: float = 0.0015
) -> float:
    """Calculate USD cost purely from token volume and rate per 1K tokens without model string mapping."""
    cost = (prompt_tokens * input_cost_per_1k / 1000.0) + (completion_tokens * output_cost_per_1k / 1000.0)
    return round(cost, 6)


class ProviderResponse(BaseModel):
    """Standardized response schema across all LLM providers."""
    generated_text: str = Field(description="The primary model output text")
    prompt_tokens: int = Field(default=0, description="Input token count")
    completion_tokens: int = Field(default=0, description="Output token count")
    total_tokens: int = Field(default=0, description="Total tokens consumed")
    latency_ms: float = Field(default=0.0, description="Execution duration in milliseconds")
    cost_usd: float = Field(default=0.0, description="Calculated USD cost")
    model_name: str = Field(description="Model identifier string")
    provider_name: str = Field(description="Provider name")
    raw_response: Optional[Dict[str, Any]] = Field(default=None, description="Raw provider metadata")


class BaseLLMProvider(ABC):
    """Unified interface that all LLM providers must implement."""

    def __init__(
        self,
        api_key: str,
        model: str,
        input_cost_per_1k: float = 0.0005,
        output_cost_per_1k: float = 0.0015
    ):
        self.api_key = api_key
        self.model = model
        self.input_cost_per_1k = input_cost_per_1k
        self.output_cost_per_1k = output_cost_per_1k

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
