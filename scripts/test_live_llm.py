"""
RAGBench Live LLM Provider & Judge Verification Script.
Executes real API calls against cloud LLM providers using BYOK credentials.
"""
import asyncio
import argparse
import os
import sys
from ragbench.providers.factory import ProviderFactory
from ragbench.evaluators.llm_judge.faithfulness import FaithfulnessEvaluator


async def run_live_provider(provider_name: str, api_key: str, model: str):
    print(f"\n[INFO] Initializing live '{provider_name}' provider with model '{model}'...")
    provider = ProviderFactory.create(provider_name, api_key=api_key, model=model)

    # 1. Test Text Generation
    print("[RUN] Sending text generation request...")
    res = await provider.generate("Explain RAG evaluation in 2 sentences.", temperature=0.0)
    print(f"[PASS] Response received in {res.latency_ms}ms | Cost: ${res.cost_usd}")
    print(f"       Generated Output: {res.generated_text.strip()}\n")

    # 2. Test LLM-as-a-Judge Evaluation
    print("[RUN] Executing live FaithfulnessEvaluator...")
    judge = FaithfulnessEvaluator(provider=provider, threshold=0.7)
    eval_res = await judge.evaluate_async(
        query="What is the company's net revenue?",
        response="The company's net revenue was $10 Million.",
        retrieved_contexts=["Net revenue for Q4 reached $10 Million."]
    )
    print(f"[PASS] Judge Metric: {eval_res.metric_name}")
    print(f"       Score: {eval_res.score} | Passed: {eval_res.passed}")
    print(f"       Reasoning: {eval_res.reason}\n")


def main():
    parser = argparse.ArgumentParser(description="Test live LLM API calls in RAGBench")
    parser.add_argument("--provider", type=str, default="groq", help="Provider name (groq, openai, anthropic, google)")
    parser.add_argument("--api-key", type=str, default=None, help="API key (or set environment variable GROQ_API_KEY, OPENAI_API_KEY, etc.)")
    parser.add_argument("--model", type=str, default=None, help="Model ID (e.g. openai/gpt-oss-120b, gpt-4o-mini, gemini-2.0-flash)")

    args = parser.parse_args()
    provider = args.provider.lower()

    env_var_map = {
        "groq": "GROQ_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GEMINI_API_KEY",
    }
    model_map = {
        "groq": "openai/gpt-oss-120b",
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-5-sonnet-20241022",
        "google": "gemini-1.5-pro",
    }

    api_key = args.api_key or os.getenv(env_var_map.get(provider, "API_KEY"))
    model = args.model or model_map.get(provider, "mock-model")

    if not api_key:
        print(f"[ERROR] No API key provided for '{provider}'. Pass --api-key <YOUR_KEY> or set {env_var_map.get(provider)}")
        sys.exit(1)

    asyncio.run(run_live_provider(provider, api_key, model))


if __name__ == "__main__":
    main()
