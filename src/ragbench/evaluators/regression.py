"""Regression Detection Engine comparing candidate experiments against baselines."""
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class RegressionReport(BaseModel):
    """Structured report produced by RegressionDetector."""
    has_regression: bool = Field(description="True if any metric score dropped beyond tolerance")
    regressed_metrics: List[str] = Field(default_factory=list, description="List of metric names that regressed")
    tolerance: float = Field(default=0.02, description="Maximum allowed score drop (e.g. 0.02 = 2%)")
    details: Dict[str, Any] = Field(description="Detailed metric-by-metric delta comparison")


class RegressionDetector:
    """Evaluates candidate experiment metric deltas against baseline metrics."""

    def __init__(self, tolerance: float = 0.02):
        self.tolerance = tolerance

    def detect_regression(
        self,
        candidate_metrics: Dict[str, float],
        baseline_metrics: Dict[str, float]
    ) -> RegressionReport:
        """Compare candidate metric averages against baseline averages."""
        regressed: List[str] = []
        details: Dict[str, Any] = {}

        all_metrics = set(candidate_metrics.keys()).union(baseline_metrics.keys())
        has_regressed = False

        for metric in all_metrics:
            cand_score = candidate_metrics.get(metric, 0.0)
            base_score = baseline_metrics.get(metric, 0.0)
            delta = round(cand_score - base_score, 4)

            is_regressed = (cand_score < (base_score - self.tolerance))
            if is_regressed:
                has_regressed = True
                regressed.append(metric)

            details[metric] = {
                "candidate_score": cand_score,
                "baseline_score": base_score,
                "delta": delta,
                "regressed": is_regressed
            }

        return RegressionReport(
            has_regression=has_regressed,
            regressed_metrics=regressed,
            tolerance=self.tolerance,
            details=details
        )
