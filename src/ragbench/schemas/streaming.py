"""Pydantic schemas for Server-Sent Events (SSE) live evaluation streaming."""
import uuid
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class StreamStartData(BaseModel):
    """Payload emitted when an evaluation run starts."""
    experiment_id: uuid.UUID
    experiment_name: str
    total_samples: int
    provider_name: str
    model_name: str
    dataset_name: Optional[str] = None


class StreamSampleData(BaseModel):
    """Payload emitted each time an individual dataset sample finishes evaluation."""
    sample_index: int = Field(..., description="1-based index of current sample")
    total_samples: int
    query: str
    response_snippet: str
    latency_ms: float
    total_tokens: int
    cost_usd: float
    metrics: Dict[str, Any] = Field(default_factory=dict)
    passed: bool
    progress_pct: float = Field(..., description="Percentage completed between 0.0 and 100.0")


class StreamCompleteData(BaseModel):
    """Payload emitted when the entire evaluation run finishes successfully."""
    experiment_id: uuid.UUID
    experiment_name: str
    total_samples: int
    successful_samples: int
    failed_samples: int
    composite_score: float
    avg_latency_ms: float
    avg_tokens: int
    total_cost_usd: float
    status: str = "SUCCESS"


class StreamErrorData(BaseModel):
    """Payload emitted when an error occurs during evaluation."""
    error_message: str
    sample_index: Optional[int] = None
    experiment_id: Optional[uuid.UUID] = None
