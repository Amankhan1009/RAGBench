"""Unit test suite for Deterministic Metric Evaluators and Engine."""
import pytest
from ragbench.evaluators.deterministic import (
    ContextOverlapEvaluator,
    ExactMatchEvaluator,
    HitRateEvaluator,
    LatencyTokenEvaluator,
    MRREvaluator,
    PrecisionAtKEvaluator,
    RecallAtKEvaluator,
)
from ragbench.evaluators.engine import EvaluationEngine


def test_exact_match_evaluator():
    evaluator = ExactMatchEvaluator(threshold=1.0)
    res_pass = evaluator.evaluate(query="Q", response="  $10 Million ", expected_output="$10 million")
    assert res_pass.passed is True
    assert res_pass.score == 1.0

    res_fail = evaluator.evaluate(query="Q", response="$10 Million", expected_output="$20 Million")
    assert res_fail.passed is False
    assert res_fail.score == 0.0


def test_retrieval_metrics():
    gt = ["Revenue was $10M in Q4.", "EBITDA reached $2.5M."]
    retrieved = [
        "Revenue was $10M in Q4.",
        "Irrelevant snippet about weather.",
        "EBITDA reached $2.5M."
    ]

    recall = RecallAtKEvaluator(k=3, threshold=0.8).evaluate(
        query="Q", response="R", ground_truth_contexts=gt, retrieved_contexts=retrieved
    )
    assert recall.score == 1.0
    assert recall.passed is True

    precision = PrecisionAtKEvaluator(k=3, threshold=0.5).evaluate(
        query="Q", response="R", ground_truth_contexts=gt, retrieved_contexts=retrieved
    )
    assert precision.score == round(2 / 3, 4)
    assert precision.passed is True

    mrr = MRREvaluator().evaluate(
        query="Q", response="R", ground_truth_contexts=gt, retrieved_contexts=retrieved
    )
    assert mrr.score == 1.0

    hit_rate = HitRateEvaluator().evaluate(
        query="Q", response="R", ground_truth_contexts=gt, retrieved_contexts=retrieved
    )
    assert hit_rate.score == 1.0


def test_context_overlap_evaluator():
    evaluator = ContextOverlapEvaluator(threshold=0.2)
    res = evaluator.evaluate(
        query="Q",
        response="Net revenue was $10M",
        retrieved_contexts=["Net revenue was reported at $10M in fiscal Q4."]
    )
    assert res.score > 0.2
    assert res.passed is True


def test_latency_token_evaluator():
    evaluator = LatencyTokenEvaluator(max_latency_ms=1000.0, max_tokens=500)
    res_ok = evaluator.evaluate(query="Q", response="R", latency_ms=450.0, total_tokens=200)
    assert res_ok.passed is True

    res_limit = evaluator.evaluate(query="Q", response="R", latency_ms=1500.0, total_tokens=600)
    assert res_limit.passed is False


def test_evaluation_engine_batch():
    engine = EvaluationEngine([
        ExactMatchEvaluator(),
        HitRateEvaluator(),
        LatencyTokenEvaluator()
    ])
    results = engine.evaluate_sample(
        query="What is net revenue?",
        response="$10 Million",
        expected_output="$10 Million",
        retrieved_contexts=["Net revenue reached $10 Million."],
        ground_truth_contexts=["Net revenue reached $10 Million."],
        latency_ms=250.0,
        total_tokens=150
    )
    assert len(results) == 3
    assert results["exact_match"].passed is True
    assert results["hit_rate"].passed is True
    assert results["performance_budget"].passed is True
