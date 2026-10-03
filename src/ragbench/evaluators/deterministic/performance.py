"""Latency and Token performance metric evaluators."""
from typing import Any, Optional

from ragbench.evaluators.base import BaseEvaluator, EvaluationResult


class LatencyTokenEvaluator(BaseEvaluator):
    """Evaluates whether latency (ms) and token counts meet budget limits."""

    def __init__(self, max_latency_ms: float = 3000.0, max_tokens: int = 4000, threshold: float = 1.0):
        super().__init__(threshold=threshold)
        self.max_latency_ms = max_latency_ms
        self.max_tokens = max_tokens

    @property
    def name(self) -> str:
        return "performance_budget"

    def evaluate(
        self,
        query: str,
        response: str,
        latency_ms: Optional[float] = None,
        total_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> EvaluationResult:
        latency_ok = (latency_ms is None) or (latency_ms <= self.max_latency_ms)
        tokens_ok = (total_tokens is None) or (total_tokens <= self.max_tokens)

        passed = latency_ok and tokens_ok
        score = 1.0 if passed else 0.0

        reasons = []
        if not latency_ok:
            reasons.append(f"Latency {latency_ms:.1f}ms exceeded budget {self.max_latency_ms}ms")
        if not tokens_ok:
            reasons.append(f"Tokens {total_tokens} exceeded budget {self.max_tokens}")

        reason = "Performance budgets satisfied." if passed else "; ".join(reasons)

        return EvaluationResult(
            metric_name=self.name,
            score=score,
            passed=passed,
            threshold=self.threshold,
            reason=reason,
            metadata={
                "latency_ms": latency_ms,
                "total_tokens": total_tokens,
                "max_latency_ms": self.max_latency_ms,
                "max_tokens": self.max_tokens,
            }
        )
