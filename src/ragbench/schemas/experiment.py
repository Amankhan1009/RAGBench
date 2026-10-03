"""Pydantic schemas for Experiments and Baseline Comparisons."""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExperimentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255, description="Experiment run name")
    description: Optional[str] = Field(default=None, description="Experiment summary")
    dataset_id: uuid.UUID = Field(description="Target dataset ID")
    provider_name: str = Field(default="mock", description="LLM provider name")
    model_name: str = Field(default="mock-model", description="Model ID")
    api_key: Optional[str] = Field(default="mock-key", description="Optional BYOK key")


class ExperimentItemResponse(BaseModel):
    id: uuid.UUID
    experiment_id: uuid.UUID
    dataset_item_id: uuid.UUID
    query: str
    response: str
    expected_output: Optional[str] = None
    metrics: Dict[str, Any] = {}
    latency_ms: float = 0.0
    total_tokens: int = 0
    cost_usd: float = 0.0
    status: str = "SUCCESS"
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


class ExperimentResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    dataset_id: uuid.UUID
    provider_name: str
    model_name: str
    status: str
    is_baseline: bool
    created_at: datetime
    items: List[ExperimentItemResponse] = []

    model_config = {"from_attributes": True}


class ComparisonDelta(BaseModel):
    candidate_experiment_id: uuid.UUID
    baseline_experiment_id: uuid.UUID
    candidate_name: str
    baseline_name: str
    metric_deltas: Dict[str, Dict[str, float]] = Field(
        description="Metric name mapping to candidate score, baseline score, and delta (+/-)"
    )
