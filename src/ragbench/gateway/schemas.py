"""Pydantic schemas for the OpenAI-compatible AI Gateway, Semantic Cache, and Budgets."""
import time
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Standard OpenAI chat message schema."""
    role: str = Field(description="Role of the message sender: 'system', 'user', or 'assistant'")
    content: str = Field(description="Textual contents of the message")


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request with extended gateway controls."""
    model: str = Field(default="openai/gpt-oss-120b", description="Model identifier")
    messages: List[ChatMessage] = Field(min_length=1, description="Ordered list of message turns")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=2500, ge=1, le=8192, description="Maximum tokens to generate")
    stream: bool = Field(default=False, description="Streaming completion (reserved for future)")


    # Extended Gateway Routing & Caching Controls
    provider: Optional[str] = Field(default=None, description="Explicit provider override (e.g. 'groq', 'google', 'mock')")
    fallback_providers: Optional[List[str]] = Field(
        default=["google", "mock"],
        description="Ordered list of providers to failover to if primary provider encounters 429/5xx errors"
    )
    cache_enabled: bool = Field(default=True, description="Whether to check and populate semantic cache")
    similarity_threshold: float = Field(
        default=0.95,
        ge=0.5,
        le=1.0,
        description="Cosine/Jaccard similarity threshold for semantic cache hits"
    )
    api_key: Optional[str] = Field(default=None, description="Optional direct BYOK key override")
    guardrails_enabled: bool = Field(default=True, description="Enforce pre-execution and post-execution AI guardrails")
    retrieved_contexts: Optional[List[str]] = Field(default=None, description="Optional retrieved RAG passages for output grounding verification")


class ChatCompletionChoice(BaseModel):
    """Standard OpenAI choice schema."""
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class UsageInfo(BaseModel):
    """Standard OpenAI token usage schema."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class GatewayMetadata(BaseModel):
    """RAGBench Gateway diagnostic and routing metadata."""
    cached: bool = Field(default=False, description="Whether response was served from cache")
    cache_key: Optional[str] = Field(default=None, description="Hash identifier of the cached query")
    latency_ms: float = Field(description="Round-trip request duration in milliseconds")
    provider_used: str = Field(description="Underlying provider that generated the response")
    model_used: str = Field(description="Model identifier executed")
    fallback_triggered: bool = Field(default=False, description="Whether automated failover rerouted this request")
    attempted_providers: List[str] = Field(default_factory=list, description="All providers evaluated in order")
    cost_usd: float = Field(default=0.0, description="Actual cost incurred for this request")
    cost_saved_usd: float = Field(default=0.0, description="Estimated cost saved if served from cache")
    guardrails_applied: bool = Field(default=False, description="Whether guardrails were evaluated")
    guardrails_blocked: bool = Field(default=False, description="Whether request was blocked by guardrails")
    guardrails_violations: List[str] = Field(default_factory=list, description="List of detected policy violations")
    guardrails_latency_ms: float = Field(default=0.0, description="Guardrails inspection latency in ms")


class ChatCompletionResponse(BaseModel):
    """Full OpenAI-compatible chat completion response with gateway metadata."""
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:12]}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionChoice]
    usage: UsageInfo
    gateway: GatewayMetadata


class BudgetConfig(BaseModel):
    """Workspace monthly spending and quota configuration."""
    monthly_budget_usd: Optional[float] = Field(default=None, ge=0.0, description="Monthly spending limit in USD")
    monthly_token_quota: Optional[int] = Field(default=None, ge=0, description="Monthly token ceiling")


class BudgetStatus(BaseModel):
    """Current cumulative budget usage for a workspace."""
    workspace_id: str
    current_month_cost_usd: float = 0.0
    current_month_tokens: int = 0
    monthly_budget_usd: Optional[float] = None
    monthly_token_quota: Optional[int] = None
    cost_usage_percentage: float = 0.0
    token_usage_percentage: float = 0.0
    budget_exceeded: bool = False


class CacheStats(BaseModel):
    """Aggregated cache performance metrics."""
    workspace_id: str
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    hit_rate: float = 0.0
    total_cost_saved_usd: float = 0.0
    total_latency_saved_ms: float = 0.0
    cached_entries_count: int = 0
