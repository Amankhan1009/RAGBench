"""Hallucination and Citation Correctness LLM-as-a-judge evaluators."""
import json
from typing import Any, Optional

from ragbench.evaluators.base import EvaluationResult
from ragbench.evaluators.llm_judge.base import LLMJudgeEvaluator


class HallucinationEvaluator(LLMJudgeEvaluator):
    """Evaluates hallucination rate (0.0 = zero hallucination, 1.0 = total hallucination)."""

    def __init__(self, provider: Any, threshold: float = 0.1):
        super().__init__(provider=provider, threshold=threshold)

    @property
    def name(self) -> str:
        return "hallucination_rate"

    async def evaluate_async(
        self,
        query: str,
        response: str,
        retrieved_contexts: Optional[list[str]] = None,
        **kwargs: Any
    ) -> EvaluationResult:
        contexts_text = "\n---\n".join(retrieved_contexts or []) if retrieved_contexts else "No context."
        prompt = (
            f"You are an expert AI Judge. Evaluate HALLUCINATION RATE.\n"
            f"Contexts:\n{contexts_text}\n\n"
            f"Response: {response}\n\n"
            f"Score 0.0 if response has ZERO hallucinations. Score 1.0 if response is completely fabricated."
        )

        provider_res = await self.provider.generate_json(prompt=prompt, schema=self._get_json_schema())

        try:
            parsed = json.loads(provider_res.generated_text)
            score = float(parsed.get("score", 0.0))
            reason = str(parsed.get("reasoning", "Evaluation completed."))
        except Exception:
            score = 1.0
            reason = f"Failed to parse JSON response: {provider_res.generated_text}"

        passed = (score <= self.threshold)

        return EvaluationResult(
            metric_name=self.name,
            score=round(score, 4),
            passed=passed,
            threshold=self.threshold,
            reason=reason,
            metadata={"model": provider_res.model_name, "provider": provider_res.provider_name}
        )

    def evaluate(self, *args: Any, **kwargs: Any) -> EvaluationResult:
        raise NotImplementedError("LLM-as-a-judge evaluators must be executed via 'evaluate_async'.")


class CitationCorrectnessEvaluator(LLMJudgeEvaluator):
    """Evaluates whether in-text citations correctly match source context snippets."""

    @property
    def name(self) -> str:
        return "citation_correctness"

    async def evaluate_async(
        self,
        query: str,
        response: str,
        retrieved_contexts: Optional[list[str]] = None,
        **kwargs: Any
    ) -> EvaluationResult:
        contexts_text = "\n---\n".join(retrieved_contexts or []) if retrieved_contexts else "No context."
        prompt = (
            f"You are an expert AI Judge. Evaluate CITATION CORRECTNESS.\n"
            f"Contexts:\n{contexts_text}\n\n"
            f"Response: {response}\n\n"
            f"Score 1.0 if all citations in response accurately reference contexts."
        )

        provider_res = await self.provider.generate_json(prompt=prompt, schema=self._get_json_schema())

        try:
            parsed = json.loads(provider_res.generated_text)
            score = float(parsed.get("score", 0.0))
            reason = str(parsed.get("reasoning", "Evaluation completed."))
        except Exception:
            score = 0.0
            reason = f"Failed to parse JSON response: {provider_res.generated_text}"

        return EvaluationResult(
            metric_name=self.name,
            score=round(score, 4),
            passed=(score >= self.threshold),
            threshold=self.threshold,
            reason=reason,
            metadata={"model": provider_res.model_name, "provider": provider_res.provider_name}
        )

    def evaluate(self, *args: Any, **kwargs: Any) -> EvaluationResult:
        raise NotImplementedError("LLM-as-a-judge evaluators must be executed via 'evaluate_async'.")
