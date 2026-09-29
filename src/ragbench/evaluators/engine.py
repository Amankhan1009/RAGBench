"""Evaluation Engine for executing batch deterministic metric evaluation suites."""
from typing import Any, Dict, List, Optional
from ragbench.evaluators.base import BaseEvaluator, EvaluationResult


class EvaluationEngine:
    """Orchestrates multi-metric evaluation across dataset items."""

    def __init__(self, evaluators: Optional[List[BaseEvaluator]] = None):
        self.evaluators: List[BaseEvaluator] = evaluators or []

    def register_evaluator(self, evaluator: BaseEvaluator) -> None:
        """Add an evaluator instance to the engine suite."""
        self.evaluators.append(evaluator)

    def evaluate_sample(
        self,
        query: str,
        response: str,
        expected_output: Optional[str] = None,
        retrieved_contexts: Optional[List[str]] = None,
        ground_truth_contexts: Optional[List[str]] = None,
        latency_ms: Optional[float] = None,
        total_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> Dict[str, EvaluationResult]:
        """Run all registered evaluators against a single sample."""
        results: Dict[str, EvaluationResult] = {}
        for evaluator in self.evaluators:
            res = evaluator.evaluate(
                query=query,
                response=response,
                expected_output=expected_output,
                retrieved_contexts=retrieved_contexts,
                ground_truth_contexts=ground_truth_contexts,
                latency_ms=latency_ms,
                total_tokens=total_tokens,
                **kwargs
            )
            results[evaluator.name] = res
        return results
