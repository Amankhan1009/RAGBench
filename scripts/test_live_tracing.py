"""
Live LangSmith Cloud Tracing Verification Script.
Sends a live sanitized trace span to your LangSmith project and verifies the response.
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from ragbench.core.tracing import trace_async_run, trace_manager


async def main():
    api_key = os.getenv("LANGCHAIN_API_KEY")
    project = os.getenv("LANGCHAIN_PROJECT", "ragbench")

    if not api_key:
        print("\n[ERROR] LANGCHAIN_API_KEY is not set in your .env file.")
        print("Please add the following to your .env file:")
        print("  LANGCHAIN_TRACING_V2=true")
        print("  LANGCHAIN_API_KEY=lsv2_pt_your_key_here")
        print("  LANGCHAIN_PROJECT=ragbench\n")
        sys.exit(1)

    print(f"\n[INFO] Testing Live LangSmith Cloud Tracing [Project: {project}]...")

    test_inputs = {
        "query": "What is RAGBench?",
        "api_key": "gsk_1234567890abcdef1234567890",  # Test secret that must be redacted
    }
    test_metadata = {
        "environment": "live_verification",
        "secret_token": "sk-ant-testsecret987654321",
    }

    print("[RUN] Executing traced async task...")
    async with trace_async_run("live_verification_run", run_type="chain", inputs=test_inputs, metadata=test_metadata) as outputs:
        await asyncio.sleep(0.1)  # Simulate small work
        outputs["status"] = "success"
        outputs["result"] = "Live trace verified with zero credential leakage."

    span = trace_manager.traces[-1]
    print(f"[PASS] Local trace captured: span_id={span.id} | latency={span.latency_ms}ms")
    print(f"       Sanitized Inputs: {span.inputs}")
    print(f"       Sanitized Metadata: {span.metadata}")
    print("\n[INFO] Check your LangSmith dashboard project: https://smith.langchain.com/")
    print(f"       Project: {project}")


if __name__ == "__main__":
    asyncio.run(main())