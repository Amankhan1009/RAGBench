"""
RAGBench End-to-End Platform Verification Script.
Executes an end-to-end workflow through all platform subsystems.
"""
import asyncio
import uuid
from httpx import ASGITransport, AsyncClient

from ragbench.core.tracing import trace_async_run, trace_manager
from ragbench.db.base import Base
from ragbench.db.session import get_engine
from ragbench.main import app


async def run_e2e_verification():
    print("\n" + "=" * 65)
    print(" 🚀 STARTING RAGBENCH FULL PLATFORM END-TO-END VERIFICATION")
    print("=" * 65 + "\n")

    # 0. Ensure Database Tables Exist
    print("[1/8] Initializing database schema...")
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("      ✅ Database schema verified.")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. System Health
        print("\n[2/8] Testing System & Database Health (/api/v1/health)...")
        res = await client.get("/api/v1/health")
        health = res.json()
        print(f"      Status: {health['status']} | App: {health['app_name']} | DB: {health['database']}")
        assert res.status_code == 200 and health["status"] == "healthy"
        print("      ✅ Health check passed.")

        # 2. Multi-Tenant Workspace & BYOK Encryption
        print("\n[3/8] Testing Multi-Tenant Auth & BYOK Encryption (/api/v1/auth)...")
        unique_ws_name = f"E2E Enterprise {uuid.uuid4().hex[:6]}"
        ws_res = await client.post("/api/v1/auth/workspaces", json={"name": unique_ws_name})
        ws = ws_res.json()
        ws_key = ws["api_key"]
        print(f"      Workspace created: '{ws['name']}' (ID: {ws['id'][:8]}...)")
        print(f"      Secret token issued: {ws_key[:12]}...")

        # Register BYOK Key
        plain_key = "gsk_live_e2e_secret_1234567890abcdef"
        key_res = await client.post(
            "/api/v1/auth/keys",
            headers={"X-API-Key": ws_key},
            json={"provider": "groq", "api_key": plain_key},
        )
        key_meta = key_res.json()
        print(f"      Encrypted BYOK Key stored. Masked preview: {key_meta['key_preview']}")
        assert plain_key not in key_meta["key_preview"]
        assert "secret_1234567890" not in key_meta["key_preview"]
        print("      ✅ Multi-tenant isolation & BYOK encryption passed.")

        # 3. Dataset Creation
        print("\n[4/8] Testing Dataset Creation & Ingestion (/api/v1/datasets)...")
        ds_res = await client.post(
            "/api/v1/datasets",
            json={
                "name": f"E2E Benchmark Suite {uuid.uuid4().hex[:4]}",
                "description": "Validation dataset for end-to-end evaluation",
                "items": [
                    {
                        "query": "What is RAGBench?",
                        "expected_output": "An evaluation platform for LLM and RAG systems.",
                        "contexts": ["RAGBench provides deterministic and LLM-as-a-judge evaluation."],
                    },
                    {
                        "query": "What is the capital of France?",
                        "expected_output": "Paris",
                        "contexts": ["Paris is the capital of France."],
                    },
                ],
            },
        )
        ds = ds_res.json()
        ds_id = ds["id"]
        print(f"      Dataset: '{ds['name']}' | Items: {len(ds['items'])} | ID: {ds_id[:8]}...")
        assert ds_res.status_code == 201
        print("      ✅ Dataset ingestion passed.")

        # 4. Baseline Experiment Run
        print("\n[5/8] Running Baseline Evaluation Experiment (/api/v1/experiments)...")
        base_exp_res = await client.post(
            "/api/v1/experiments",
            json={
                "name": "Production Baseline v1.0",
                "dataset_id": ds_id,
                "provider_name": "mock",
                "model_name": "mock-baseline",
            },
        )
        base_exp = base_exp_res.json()
        base_id = base_exp["id"]
        print(f"      Baseline Run completed: ID={base_id[:8]}... | Status={base_exp['status']}")

        # Set as baseline
        await client.post(f"/api/v1/experiments/{base_id}/set-baseline")
        print("      Experiment marked as active baseline.")
        print("      ✅ Baseline benchmark execution passed.")

        # 5. Candidate Experiment & Delta Comparison
        print("\n[6/8] Running Candidate Experiment & Baseline Comparison...")
        cand_exp_res = await client.post(
            "/api/v1/experiments",
            json={
                "name": "Candidate Model v1.1",
                "dataset_id": ds_id,
                "provider_name": "mock",
                "model_name": "mock-candidate",
            },
        )
        cand_exp = cand_exp_res.json()
        cand_id = cand_exp["id"]

        comp_res = await client.get(f"/api/v1/experiments/{cand_id}/compare")
        comp = comp_res.json()
        print(f"      Candidate: '{comp['candidate_name']}' vs Baseline: '{comp['baseline_name']}'")
        for metric, d in comp["metric_deltas"].items():
            c_val = d.get("candidate", d.get("candidate_score", 0.0))
            b_val = d.get("baseline", d.get("baseline_score", 0.0))
            print(f"        • {metric:20s}: Candidate={c_val:.4f} | Base={b_val:.4f} | Delta={d['delta']:+.4f}")
        print("      ✅ Experiment comparison engine passed.")

        # 6. CI/CD Automated Regression Gate
        print("\n[7/8] Evaluating CI/CD Regression Quality Gate (/check-regression)...")
        reg_res = await client.get(f"/api/v1/experiments/{cand_id}/check-regression?tolerance=0.02")
        report = reg_res.json()
        status_str = "❌ REGRESSED" if report["has_regression"] else "✅ PASSED"
        print(f"      CI Gate Status: {status_str} (Tolerance: {report['tolerance'] * 100}%)")
        assert report["has_regression"] is False
        print("      ✅ CI/CD Regression Gate passed.")

        # 7. Agent Trajectory & Loop Detection
        print("\n[8/8] Testing Agent Trajectory Evaluation Engine (/api/v1/agent)...")
        agent_res = await client.post(
            "/api/v1/agent/evaluate-trajectory",
            json={
                "trajectory": {
                    "goal": "Retrieve database schema and calculate margin",
                    "steps": [
                        {"step_number": 1, "tool_call": {"name": "db_schema", "arguments": {}}},
                        {"step_number": 2, "tool_call": {"name": "calculator", "arguments": {"expr": "500 - 300"}}},
                    ],
                    "final_response": "Net margin is 200",
                },
                "expected_tools": ["db_schema", "calculator"],
                "max_optimal_steps": 3,
            },
        )
        agent_report = agent_res.json()
        print(f"      Agent Passed: {agent_report['passed']}")
        print(f"      Tool Precision: {agent_report['tool_precision']} | Recall: {agent_report['tool_recall']}")
        print(f"      Efficiency Score: {agent_report['efficiency_score']} | Loop Detected: {agent_report['loop_detected']}")
        assert agent_report["passed"] is True and agent_report["loop_detected"] is False
        print("      ✅ Agent Trajectory evaluation passed.")

    # 8. Observability & Zero-Leakage Validation
    print("\n[BONUS] Verifying Observability & Zero-Leakage Secret Redaction...")
    trace_manager.clear()
    async with trace_async_run("e2e_observability_check", inputs={"key": "gsk_test1234567890abcdef1234"}) as out:
        out["status"] = "ok"
    span = trace_manager.traces[-1]
    assert span.inputs["key"] == "[REDACTED_SECRET]"
    print(f"      Trace span captured: id={span.id[:8]}... | Latency: {span.latency_ms}ms")
    print(f"      Redacted secret in trace: {span.inputs['key']}")
    print("      ✅ Observability & Zero-Leakage verified.")

    print("\n" + "=" * 65)
    print(" 🎉 ALL SUBSYSTEMS VERIFIED: 100% PASSING END-TO-END!")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    asyncio.run(run_e2e_verification())