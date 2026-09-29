"""Base class for LLM-as-a-Judge evaluators routing via BaseLLMProvider."""
from typing import Any, Dict, Optional
from ragbench.evaluators.base import BaseEvaluator, EvaluationResult
from ragbench.providers.base import BaseLLMProvider


class LLMJudgeEvaluator(BaseEvaluator):
    """Abstract evaluator utilizing RAGBench model-independent LLM provider for judgment."""

    def __init__(self, provider: BaseLLMProvider, threshold: float = 0.7):
        super().__init__(threshold=threshold)
        self.provider = provider

    def _get_json_schema(self) -> Dict[str, Any]:
        """JSON schema enforcing structured LLM judge output."""
        return {
            "type": "object",
            "properties": {
                "score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "reasoning": {"type": "string"}
            },
            "required": ["score", "reasoning"]
        }
