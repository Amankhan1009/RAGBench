"""Deterministic retrieval evaluators: Recall@K, Precision@K, MRR, Hit Rate, and Context Overlap."""
from typing import Any, Optional, Set
from ragbench.evaluators.base import BaseEvaluator, EvaluationResult


def _normalize_tokens(text: str) -> Set[str]:
    """Tokenize and normalize text into word set."""
    return set(text.lower().strip().split())


class RecallAtKEvaluator(BaseEvaluator):
    """Measures fraction of ground-truth context chunks present in retrieved context top-k."""

    def __init__(self, k: int = 5, threshold: float = 0.7):
        super().__init__(threshold=threshold)
        self.k = k

    @property
    def name(self) -> str:
        return f"recall_at_{self.k}"

    def evaluate(
        self,
        query: str,
        response: str,
        expected_output: Optional[str] = None,
        retrieved_contexts: Optional[list[str]] = None,
        ground_truth_contexts: Optional[list[str]] = None,
        **kwargs: Any
    ) -> EvaluationResult:
        if not ground_truth_contexts:
            return EvaluationResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                threshold=self.threshold,
                reason="Ground-truth contexts missing for Recall calculation."
            )

        top_k_retrieved = (retrieved_contexts or [])[: self.k]
        if not top_k_retrieved:
            return EvaluationResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                threshold=self.threshold,
                reason="No retrieved contexts provided."
            )

        retrieved_tokens = set().union(*[_normalize_tokens(c) for c in top_k_retrieved])
        matched = 0

        for gt_ctx in ground_truth_contexts:
            gt_tokens = _normalize_tokens(gt_ctx)
            if gt_tokens and len(gt_tokens.intersection(retrieved_tokens)) / len(gt_tokens) >= 0.5:
                matched += 1

        score = round(matched / len(ground_truth_contexts), 4)

        return EvaluationResult(
            metric_name=self.name,
            score=score,
            passed=(score >= self.threshold),
            threshold=self.threshold,
            reason=f"Retrieved {matched}/{len(ground_truth_contexts)} ground-truth contexts in top-{self.k}."
        )


class PrecisionAtKEvaluator(BaseEvaluator):
    """Measures fraction of top-k retrieved context chunks that are relevant to ground-truth."""

    def __init__(self, k: int = 5, threshold: float = 0.7):
        super().__init__(threshold=threshold)
        self.k = k

    @property
    def name(self) -> str:
        return f"precision_at_{self.k}"

    def evaluate(
        self,
        query: str,
        response: str,
        expected_output: Optional[str] = None,
        retrieved_contexts: Optional[list[str]] = None,
        ground_truth_contexts: Optional[list[str]] = None,
        **kwargs: Any
    ) -> EvaluationResult:
        top_k_retrieved = (retrieved_contexts or [])[: self.k]
        if not top_k_retrieved or not ground_truth_contexts:
            return EvaluationResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                threshold=self.threshold,
                reason="Missing retrieved contexts or ground-truth contexts."
            )

        gt_tokens_all = set().union(*[_normalize_tokens(c) for c in ground_truth_contexts])
        relevant_count = 0

        for ret_ctx in top_k_retrieved:
            ret_tokens = _normalize_tokens(ret_ctx)
            if ret_tokens and len(ret_tokens.intersection(gt_tokens_all)) / len(ret_tokens) >= 0.3:
                relevant_count += 1

        score = round(relevant_count / len(top_k_retrieved), 4)

        return EvaluationResult(
            metric_name=self.name,
            score=score,
            passed=(score >= self.threshold),
            threshold=self.threshold,
            reason=f"{relevant_count}/{len(top_k_retrieved)} top-{self.k} contexts matched ground-truth."
        )


class MRREvaluator(BaseEvaluator):
    """Calculates Mean Reciprocal Rank (1/rank) of first relevant retrieved context chunk."""

    def __init__(self, threshold: float = 0.5):
        super().__init__(threshold=threshold)

    @property
    def name(self) -> str:
        return "mrr"

    def evaluate(
        self,
        query: str,
        response: str,
        expected_output: Optional[str] = None,
        retrieved_contexts: Optional[list[str]] = None,
        ground_truth_contexts: Optional[list[str]] = None,
        **kwargs: Any
    ) -> EvaluationResult:
        if not retrieved_contexts or not ground_truth_contexts:
            return EvaluationResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                threshold=self.threshold,
                reason="Missing retrieved contexts or ground-truth contexts for MRR."
            )

        gt_tokens_all = set().union(*[_normalize_tokens(c) for c in ground_truth_contexts])

        for rank_idx, ret_ctx in enumerate(retrieved_contexts, start=1):
            ret_tokens = _normalize_tokens(ret_ctx)
            if ret_tokens and len(ret_tokens.intersection(gt_tokens_all)) / len(ret_tokens) >= 0.3:
                mrr_score = round(1.0 / rank_idx, 4)
                return EvaluationResult(
                    metric_name=self.name,
                    score=mrr_score,
                    passed=(mrr_score >= self.threshold),
                    threshold=self.threshold,
                    reason=f"First relevant context found at rank {rank_idx} (MRR: {mrr_score})."
                )

        return EvaluationResult(
            metric_name=self.name,
            score=0.0,
            passed=False,
            threshold=self.threshold,
            reason="No relevant context found in retrieved results."
        )


class HitRateEvaluator(BaseEvaluator):
    """Binary check (1.0 or 0.0) indicating if at least one relevant context chunk was retrieved."""

    def __init__(self, threshold: float = 1.0):
        super().__init__(threshold=threshold)

    @property
    def name(self) -> str:
        return "hit_rate"

    def evaluate(
        self,
        query: str,
        response: str,
        expected_output: Optional[str] = None,
        retrieved_contexts: Optional[list[str]] = None,
        ground_truth_contexts: Optional[list[str]] = None,
        **kwargs: Any
    ) -> EvaluationResult:
        mrr_eval = MRREvaluator(threshold=0.01).evaluate(
            query=query,
            response=response,
            retrieved_contexts=retrieved_contexts,
            ground_truth_contexts=ground_truth_contexts
        )
        hit_score = 1.0 if mrr_eval.score > 0.0 else 0.0
        return EvaluationResult(
            metric_name=self.name,
            score=hit_score,
            passed=(hit_score >= self.threshold),
            threshold=self.threshold,
            reason="Hit found in retrieved contexts." if hit_score == 1.0 else "No relevant context retrieved."
        )


class ContextOverlapEvaluator(BaseEvaluator):
    """Jaccard token overlap similarity between retrieved contexts and expected output."""

    def __init__(self, threshold: float = 0.5):
        super().__init__(threshold=threshold)

    @property
    def name(self) -> str:
        return "context_overlap"

    def evaluate(
        self,
        query: str,
        response: str,
        expected_output: Optional[str] = None,
        retrieved_contexts: Optional[list[str]] = None,
        **kwargs: Any
    ) -> EvaluationResult:
        target_text = expected_output or response
        target_tokens = _normalize_tokens(target_text)
        if not target_tokens or not retrieved_contexts:
            return EvaluationResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                threshold=self.threshold,
                reason="Missing target text or retrieved contexts."
            )

        context_tokens = set().union(*[_normalize_tokens(c) for c in retrieved_contexts])
        if not context_tokens:
            return EvaluationResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                threshold=self.threshold,
                reason="Contexts container contains no valid tokens."
            )

        intersection = len(target_tokens.intersection(context_tokens))
        union = len(target_tokens.union(context_tokens))
        jaccard_score = round(intersection / union, 4) if union > 0 else 0.0

        return EvaluationResult(
            metric_name=self.name,
            score=jaccard_score,
            passed=(jaccard_score >= self.threshold),
            threshold=self.threshold,
            reason=f"Jaccard token overlap: {jaccard_score}."
        )
