"""Exact Match evaluator."""
from typing import Any, Optional
from ragbench.evaluators.base import BaseEvaluator, EvaluationResult


class ExactMatchEvaluator(BaseEvaluator):
    """Evaluates whether generated response matches expected output exactly (case/whitespace normalized)."""

    def __init__(self, threshold: float = 1.0, ignore_case: bool = True, strip_whitespace: bool = True):
        super().__init__(threshold=threshold)
        self.ignore_case = ignore_case
        self.strip_whitespace = strip_whitespace

    @property
    def name(self) -> str:
        return "exact_match"

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
        if not expected_output:
            return EvaluationResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                threshold=self.threshold,
                reason="Expected output missing for exact match evaluation."
            )

        resp_clean = response
        exp_clean = expected_output

        if self.strip_whitespace:
            resp_clean = resp_clean.strip()
            exp_clean = exp_clean.strip()

        if self.ignore_case:
            resp_clean = resp_clean.lower()
            exp_clean = exp_clean.lower()

        matched = (resp_clean == exp_clean)
        score = 1.0 if matched else 0.0

        return EvaluationResult(
            metric_name=self.name,
            score=score,
            passed=(score >= self.threshold),
            threshold=self.threshold,
            reason="Response matches expected output exactly." if matched else "Response differs from expected output."
        )
