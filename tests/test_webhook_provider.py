"""Unit and integration tests for WebhookProvider & Custom RAG Endpoint integration."""
import pytest

from ragbench.evaluators.deterministic import ExactMatchEvaluator, HitRateEvaluator
from ragbench.evaluators.engine import EvaluationEngine
from ragbench.providers.factory import ProviderFactory
from ragbench.providers.webhook import WebhookProvider


def test_webhook_provider_registration():
    provider = ProviderFactory.create(
        "webhook",
        api_key="secret-token",
        model="https://api.example.com/rag/query",
    )
    assert isinstance(provider, WebhookProvider)
    assert provider.webhook_url == "https://api.example.com/rag/query"

    custom_provider = ProviderFactory.create(
        "custom",
        api_key="secret-token-2",
        model="https://internal.service.io/v1/predict",
    )
    assert isinstance(custom_provider, WebhookProvider)


def test_webhook_provider_invalid_url():
    with pytest.raises(ValueError, match="Invalid webhook URL"):
        ProviderFactory.create("webhook", api_key="", model="not-a-valid-url")

    with pytest.raises(ValueError, match="requires a valid HTTP/HTTPS endpoint URL"):
        ProviderFactory.create("webhook", api_key="", model="")


@pytest.mark.asyncio
async def test_webhook_provider_generate_standard_json(httpx_mock):
    webhook_url = "https://api.example.com/rag/v1/query"
    httpx_mock.add_response(
        url=webhook_url,
        method="POST",
        json={
            "answer": "Quantum computing uses qubits instead of bits.",
            "contexts": ["Qubits can exist in superposition states.", "Quantum entanglement."],
        },
    )

    provider = ProviderFactory.create(
        "webhook",
        api_key="token_123",
        model=webhook_url,
        response_path="answer",
        contexts_path="contexts",
    )

    res = await provider.generate("What is quantum computing?")
    assert res.generated_text == "Quantum computing uses qubits instead of bits."
    assert res.provider_name == "Webhook"
    assert res.model_name == webhook_url
    assert res.latency_ms >= 0.0
    assert res.raw_response is not None
    assert res.raw_response.get("retrieved_contexts") == [
        "Qubits can exist in superposition states.",
        "Quantum entanglement.",
    ]


@pytest.mark.asyncio
async def test_webhook_provider_nested_dot_path(httpx_mock):
    webhook_url = "https://my-rag.internal/endpoint"
    httpx_mock.add_response(
        url=webhook_url,
        method="POST",
        json={
            "status": "success",
            "payload": {
                "results": [
                    {
                        "generated_text": "Nested response extracted via dot notation.",
                        "retrieved_chunks": ["Source document A"],
                    }
                ]
            },
        },
    )

    provider = ProviderFactory.create(
        "webhook",
        api_key="",
        model=webhook_url,
        response_path="payload.results.0.generated_text",
        contexts_path="payload.results.0.retrieved_chunks",
    )

    res = await provider.generate("Extract test")
    assert res.generated_text == "Nested response extracted via dot notation."
    assert res.raw_response["retrieved_contexts"] == ["Source document A"]


@pytest.mark.asyncio
async def test_webhook_provider_plain_text(httpx_mock):
    webhook_url = "https://plain-text-rag.org/ask"
    httpx_mock.add_response(
        url=webhook_url,
        method="POST",
        text="Plain text generated output with no JSON wrapping.",
        headers={"Content-Type": "text/plain"},
    )

    provider = ProviderFactory.create("webhook", api_key="", model=webhook_url)
    res = await provider.generate("Give me plain text")
    assert res.generated_text == "Plain text generated output with no JSON wrapping."


@pytest.mark.asyncio
async def test_webhook_provider_auth_and_custom_headers(httpx_mock):
    webhook_url = "https://secure-rag.net/chat"

    httpx_mock.add_response(
        url=webhook_url,
        method="POST",
        json={"response": "Authenticated successfully"},
    )

    provider = ProviderFactory.create(
        "webhook",
        api_key="my-secret-jwt",
        model=webhook_url,
        headers={"X-Custom-Tenant": "engineering"},
    )

    res = await provider.generate("Hello with custom headers")
    assert res.generated_text == "Authenticated successfully"

    sent_req = httpx_mock.get_request()
    assert sent_req.headers.get("authorization") == "Bearer my-secret-jwt"
    assert sent_req.headers.get("x-custom-tenant") == "engineering"



@pytest.mark.asyncio
async def test_webhook_provider_error_handling(httpx_mock):
    webhook_url = "https://failing-rag.com/api"
    httpx_mock.add_response(
        url=webhook_url,
        method="POST",
        status_code=500,
        text="Internal Server Error: Database connection lost",
    )

    provider = ProviderFactory.create("webhook", api_key="", model=webhook_url)

    with pytest.raises(RuntimeError, match="Webhook call returned HTTP 500"):
        await provider.generate("Test error")


@pytest.mark.asyncio
async def test_webhook_provider_generate_json(httpx_mock):
    webhook_url = "https://json-rag.com/generate"
    httpx_mock.add_response(
        url=webhook_url,
        method="POST",
        json={"answer": '{"key": "value", "score": 0.95}'},
    )

    provider = ProviderFactory.create("webhook", api_key="", model=webhook_url)
    res = await provider.generate_json("Generate JSON", schema={"type": "object"})
    assert '{"key": "value", "score": 0.95}' in res.generated_text


@pytest.mark.asyncio
async def test_webhook_provider_full_evaluation_pipeline(httpx_mock):
    webhook_url = "https://custom-rag.internal/v1/search_and_answer"
    httpx_mock.add_response(
        url=webhook_url,
        method="POST",
        json={
            "answer": "Photosynthesis produces glucose and oxygen.",
            "contexts": [
                "Photosynthesis is the process used by plants to convert light energy into chemical energy.",
                "Oxygen is released as a byproduct of water photolysis.",
            ],
        },
    )

    provider = ProviderFactory.create("webhook", api_key="test-rag-key", model=webhook_url)
    gen_res = await provider.generate("Explain photosynthesis output")

    engine = EvaluationEngine([ExactMatchEvaluator(), HitRateEvaluator()])

    eval_dict = engine.evaluate_sample(
        query="Explain photosynthesis output",
        response=gen_res.generated_text,
        expected_output="Photosynthesis produces glucose and oxygen.",
        retrieved_contexts=gen_res.raw_response["retrieved_contexts"],
        ground_truth_contexts=[
            "Photosynthesis is the process used by plants to convert light energy into chemical energy."
        ],
    )

    assert eval_dict["exact_match"].score == 1.0
    assert eval_dict["exact_match"].passed is True
    assert eval_dict["hit_rate"].score == 1.0
    assert eval_dict["hit_rate"].passed is True

