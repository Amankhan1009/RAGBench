"""Pydantic schemas for Production Traffic Shadowing and Golden Set Harvester."""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class TrafficSampleIngest(BaseModel):
    user_query: str = Field(..., description="Raw production user prompt / query", min_length=1)
    model_response: Optional[str] = Field(default=None, description="Model generation output")
    retrieved_contexts: Optional[List[str]] = Field(default=None, description="Context chunks passed to model")
    latency_ms: Optional[float] = Field(default=None, description="End-to-end execution latency in milliseconds")
    token_count: Optional[int] = Field(default=None, description="Total tokens consumed (prompt + completion)")
    cost_usd: Optional[float] = Field(default=None, description="Estimated inference cost in USD")
    provider: Optional[str] = Field(default=None, description="LLM provider name (e.g. groq, openai, webhook)")
    model: Optional[str] = Field(default=None, description="Model identifier used in production")
    guardrails_triggered: Optional[bool] = Field(default=False, description="Whether guardrails were triggered")
    guardrails_violations: Optional[List[str]] = Field(default=None, description="List of guardrail violation tags")
    confidence_score: Optional[float] = Field(default=None, description="Self-reported or evaluated confidence (0.0 to 1.0)")
    session_id: Optional[str] = Field(default=None, description="Optional caller session or correlation ID")
    sample_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Arbitrary production metadata")


class TrafficSampleBatchIngest(BaseModel):
    samples: List[TrafficSampleIngest] = Field(..., min_length=1, max_length=100)


class TrafficSampleResponse(BaseModel):
    id: str
    workspace_id: str
    session_id: Optional[str] = None
    user_query: str
    model_response: Optional[str] = None
    retrieved_contexts: Optional[List[str]] = None
    latency_ms: Optional[float] = None
    token_count: Optional[int] = None
    cost_usd: Optional[float] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    guardrails_triggered: bool = False
    guardrails_violations: Optional[List[str]] = None
    confidence_score: Optional[float] = None
    is_flagged: bool = False
    flag_reason: Optional[str] = None
    is_promoted: bool = False
    promoted_to_dataset_id: Optional[str] = None
    sample_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    @field_validator("id", "workspace_id", "promoted_to_dataset_id", mode="before")
    @classmethod
    def coerce_uuid_to_str(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, uuid.UUID):
            return str(v)
        return str(v)

    model_config = {"from_attributes": True}


class TrafficSampleListResponse(BaseModel):
    items: List[TrafficSampleResponse]
    total: int
    page: int
    limit: int
    flagged_count: int


class TrafficStatsResponse(BaseModel):
    total_samples: int
    flagged_count: int
    anomaly_rate_percent: float
    promoted_count: int
    reasons_breakdown: Dict[str, int]
    provider_breakdown: Dict[str, int]
    avg_latency_ms: float
    p95_latency_ms: float


class GoldenSetPromotionRequest(BaseModel):
    sample_ids: List[str] = Field(..., min_length=1, description="List of traffic sample IDs to promote")
    target_dataset_id: Optional[str] = Field(default=None, description="Target existing dataset ID")
    new_dataset_name: Optional[str] = Field(default=None, description="Name if creating a new dataset")
    new_dataset_description: Optional[str] = Field(default=None, description="Description for new dataset")


class GoldenSetPromotionResponse(BaseModel):
    dataset_id: str
    dataset_name: str
    promoted_count: int
    created_new: bool
    promoted_sample_ids: List[str]
    message: str
