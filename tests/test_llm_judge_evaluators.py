"""Unit test suite for LLM-as-a-Judge evaluators using MockLLMProvider."""
import pytest
from ragbench.evaluators.llm_judge import (
    AnswerRelevancyEvaluator,
    CitationCorrectnessEvaluator,
    FaithfulnessEvaluator,
    GroundednessEvaluator,
    HallucinationEvaluator,
)
from ragbench.providers.mock import MockLLMProvider


@pytest.mark.asyncio
async def test_faithfulness_evaluator():
    mock_provider = MockLLMProvider()
    evaluator = FaithfulnessEvaluator(provider=mock_provider, threshold=0.7)

    res = await evaluator.evaluate_async(
        query="What is net revenue?",
        response="Net revenue was $10M.",
        retrieved_contexts=["Net revenue reached $10M."]
    )
    assert res.metric_name == "faithfulness"
    assert res.passed is True
    assert res.score == 1.0


@pytest.mark.asyncio
async def test_answer_relevancy_and_groundedness_evaluators():
    mock_provider = MockLLMProvider()

    relevancy_eval = AnswerRelevancyEvaluator(provider=mock_provider, threshold=0.7)
    rel_res = await relevancy_eval.evaluate_async(query="Q", response="A")
    assert rel_res.passed is True
    assert rel_res.score == 1.0

    groundedness_eval = GroundednessEvaluator(provider=mock_provider, threshold=0.7)
    gnd_res = await groundedness_eval.evaluate_async(query="Q", response="A", retrieved_contexts=["C"])
    assert gnd_res.passed is True
    assert gnd_res.score == 1.0


@pytest.mark.asyncio
async def test_hallucination_and_citation_evaluators():
    mock_provider = MockLLMProvider()

    hallucination_eval = HallucinationEvaluator(provider=mock_provider, threshold=0.1)
    hal_res = await hallucination_eval.evaluate_async(query="Q", response="A", retrieved_contexts=["C"])
    assert hal_res.metric_name == "hallucination_rate"

    citation_eval = CitationCorrectnessEvaluator(provider=mock_provider, threshold=0.7)
    cit_res = await citation_eval.evaluate_async(query="Q", response="A [1]", retrieved_contexts=["C"])
    assert cit_res.passed is True
