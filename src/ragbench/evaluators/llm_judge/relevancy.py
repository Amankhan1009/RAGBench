"""Answer Relevancy and Groundedness LLM-as-a-judge evaluators."""
import json
from typing import Any, Optional
from ragbench.evaluators.base import EvaluationResult
from ragbench.evaluators.llm_judge.base import LLMJudgeEvaluator


class AnswerRelevancyEvaluator(LLMJudgeEvaluator):
    """Evaluates how directly generated response answers user query."""

    @property
    def name(self) -> str:
        return "answer_relevancy"

    async def evaluate_async(
        self,
        query: str,
        response: str,
        **kwargs: Any
    ) -> EvaluationResult:
        prompt = (
            f"You are an expert AI Judge. Evaluate the ANSWER RELEVANCY of the response to the user query.\n"
            f"Query: {query}\n"
            f"Response: {response}\n\n"
            f"Score 1.0 if response directly and completely answers query without fluff."
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


class GroundednessEvaluator(LLMJudgeEvaluator):
    """Evaluates context grounding of response."""

    @property
    def name(self) -> str:
        return "groundedness"

    async def evaluate_async(
        self,
        query: str,
        response: str,
        retrieved_contexts: Optional[list[str]] = None,
        **kwargs: Any
    ) -> EvaluationResult:
        contexts_text = "\n---\n".join(retrieved_contexts or []) if retrieved_contexts else "No context."
        prompt = (
            f"You are an expert AI Judge. Evaluate GROUNDEDNESS of response against contexts.\n"
            f"Contexts:\n{contexts_text}\n\n"
            f"Response: {response}\n\n"
            f"Score 1.0 if response statements are strictly grounded in contexts."
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
