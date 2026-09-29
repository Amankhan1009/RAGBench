"""Base interfaces and schema for evaluation metrics."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class EvaluationResult(BaseModel):
    """Standardized output result produced by any evaluator metric."""
    metric_name: str = Field(description="Name of the evaluation metric")
    score: float = Field(description="Numeric score between 0.0 and 1.0 or value")
    passed: bool = Field(description="Whether the score met the pass threshold")
    threshold: float = Field(default=0.7, description="Threshold required for pass")
    reason: str = Field(default="", description="Detailed score explanation or failure reason")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metric execution metadata")


class BaseEvaluator(ABC):
    """Abstract base class for all deterministic and LLM-based evaluators."""

    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this metric."""
        pass

    @abstractmethod
    def evaluate(
        self,
        query: str,
        response: str,
        expected_output: Optional[str] = None,
        retrieved_contexts: Optional[list[str]] = None,
        ground_truth_contexts: Optional[list[str]] = None,
        latency_ms: Optional[float] = None,
        total_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> EvaluationResult:
        """Execute evaluation logic and return EvaluationResult."""
        pass
