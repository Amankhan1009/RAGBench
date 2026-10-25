"""Schemas for Pareto Frontier, Radar Metrics, and Quality Trends analytics."""
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ParetoPoint(BaseModel):
    experiment_id: uuid.UUID
    name: str
    model_name: str
    provider_name: str
    composite_score: float = Field(description="Aggregated quality score from 0.0 to 1.0")
    latency_ms: float = Field(description="Average latency in milliseconds")
    cost_usd: float = Field(default=0.0, description="Average cost in USD")
    total_tokens: int = Field(default=0, description="Average token consumption")
    metrics: Dict[str, float] = Field(default_factory=dict, description="Detailed metric averages")
    is_pareto_optimal: bool = Field(default=False, description="Whether this point lies on the Pareto frontier")
    is_baseline: bool = Field(default=False, description="Whether this experiment is the active baseline")
    created_at: datetime


class RadarDimension(BaseModel):
    dimension: str
    candidate_score: float
    baseline_score: float


class TrendPoint(BaseModel):
    experiment_id: uuid.UUID
    name: str
    timestamp: str
    composite_score: float
    latency_ms: float
    is_baseline: bool


class ParetoAnalyticsResponse(BaseModel):
    total_experiments: int
    points: List[ParetoPoint]
    pareto_frontier: List[ParetoPoint]
    radar_comparison: Optional[List[RadarDimension]] = None
    candidate_name: Optional[str] = None
    baseline_name: Optional[str] = None
    trends: List[TrendPoint]
