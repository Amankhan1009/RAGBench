import os
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ragbench.api.v1.auth import get_current_workspace
from ragbench.core.security import decrypt_api_key
from ragbench.core.tracing import trace_async_run
from ragbench.db.session import get_db, get_session_factory
from ragbench.evaluators.analytics import calculate_pareto_frontier
from ragbench.evaluators.deterministic import (
    ExactMatchEvaluator,
    HitRateEvaluator,
    LatencyTokenEvaluator,
)
from ragbench.evaluators.engine import EvaluationEngine
from ragbench.evaluators.regression import RegressionDetector, RegressionReport
from ragbench.models.dataset import Dataset
from ragbench.models.experiment import Experiment, ExperimentItem
from ragbench.models.workspace import Workspace, WorkspaceApiKey
from ragbench.providers.factory import ProviderFactory
from ragbench.schemas.analytics import ParetoAnalyticsResponse
from ragbench.schemas.experiment import (
    ComparisonDelta,
    ExperimentCreate,
    ExperimentResponse,
)
from ragbench.schemas.streaming import (
    StreamCompleteData,
    StreamErrorData,
    StreamSampleData,
    StreamStartData,
)

router = APIRouter(prefix="/experiments", tags=["Experiments"])


@router.post("", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_experiment(
    payload: ExperimentCreate,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Launch an evaluation experiment across dataset items within the active workspace."""
    stmt = select(Dataset).where(
        Dataset.id == payload.dataset_id,
        Dataset.workspace_id == workspace.id,
    )
    dataset = (await db.execute(stmt)).scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset '{payload.dataset_id}' not found in active workspace.")

    effective_key = payload.api_key
    if not effective_key or (effective_key == "mock-key" and payload.provider_name.lower() != "mock"):
        if payload.provider_name.lower() == "mock":
            effective_key = "mock-key"
        else:
            key_stmt = select(WorkspaceApiKey).where(
                WorkspaceApiKey.workspace_id == workspace.id,
                WorkspaceApiKey.provider == payload.provider_name.lower(),
            )
            key_record = (await db.execute(key_stmt)).scalar_one_or_none()
            if key_record:
                try:
                    effective_key = decrypt_api_key(key_record.encrypted_key)
                except Exception:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to decrypt stored provider API key. Please re-register your key in the BYOK tab.",
                    )
            else:
                env_fallback = os.getenv(f"{payload.provider_name.upper()}_API_KEY")
                if env_fallback:
                    effective_key = env_fallback
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"No API key configured for provider '{payload.provider_name}'. Please add your API key in the 'API Keys (BYOK)' tab or pass it directly.",
                    )

    try:
        provider = ProviderFactory.create(payload.provider_name, api_key=effective_key, model=payload.model_name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to instantiate provider: {str(exc)}")

    engine = EvaluationEngine([ExactMatchEvaluator(), HitRateEvaluator(), LatencyTokenEvaluator()])

    experiment = Experiment(
        name=payload.name,
        description=payload.description,
        dataset_id=payload.dataset_id,
        workspace_id=workspace.id,
        provider_name=payload.provider_name,
        model_name=payload.model_name,
        status="RUNNING"
    )
    db.add(experiment)
    await db.flush()

    for ds_item in dataset.items:
        try:
            async with trace_async_run(
                name=f"{payload.provider_name.capitalize()} - {payload.model_name or 'default'}",
                run_type="llm",
                inputs={"query": ds_item.query, "dataset_id": str(dataset.id)},
                metadata={
                    "experiment_name": payload.name,
                    "provider": payload.provider_name,
                    "model": payload.model_name or "default",
                    "dataset_item_id": str(ds_item.id),
                    "workspace": workspace.name,
                },
            ) as trace_outputs:
                gen_res = await provider.generate(ds_item.query)
                eval_dict = engine.evaluate_sample(
                    query=ds_item.query,
                    response=gen_res.generated_text,
                    expected_output=ds_item.expected_output,
                    retrieved_contexts=ds_item.contexts,
                    ground_truth_contexts=ds_item.contexts,
                    latency_ms=gen_res.latency_ms,
                    total_tokens=gen_res.total_tokens,
                )
                metrics_payload = {k: {"score": v.score, "passed": v.passed, "reason": v.reason} for k, v in eval_dict.items()}

                trace_outputs["output"] = gen_res.generated_text
                trace_outputs["metrics"] = {k: v["score"] for k, v in metrics_payload.items()}
                trace_outputs["latency_ms"] = gen_res.latency_ms
                trace_outputs["total_tokens"] = gen_res.total_tokens
                trace_outputs["cost_usd"] = gen_res.cost_usd

                exp_item = ExperimentItem(
                    experiment_id=experiment.id,
                    dataset_item_id=ds_item.id,
                    query=ds_item.query,
                    response=gen_res.generated_text,
                    expected_output=ds_item.expected_output,
                    metrics=metrics_payload,
                    latency_ms=gen_res.latency_ms,
                    total_tokens=gen_res.total_tokens,
                    cost_usd=gen_res.cost_usd,
                    status="SUCCESS",
                )
        except Exception as exc:
            exp_item = ExperimentItem(
                experiment_id=experiment.id,
                dataset_item_id=ds_item.id,
                query=ds_item.query,
                response="",
                expected_output=ds_item.expected_output,
                metrics={},
                status="FAILED",
                error_message=str(exc)
            )
        db.add(exp_item)

    experiment.status = "COMPLETED"
    await db.commit()
    await db.refresh(experiment)
    return experiment


@router.post("/stream")
async def create_experiment_stream(
    payload: ExperimentCreate,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Launch an evaluation experiment and stream real-time progress events (SSE) per sample."""
    stmt = select(Dataset).where(
        Dataset.id == payload.dataset_id,
        Dataset.workspace_id == workspace.id,
    )
    dataset = (await db.execute(stmt)).scalar_one_or_none()
    if not dataset:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset '{payload.dataset_id}' not found in active workspace.",
        )
    if not dataset.items:
        raise HTTPException(
            status_code=400,
            detail="Cannot run evaluation on an empty dataset. Please add dataset items first.",
        )

    effective_key = payload.api_key
    if not effective_key or (effective_key == "mock-key" and payload.provider_name.lower() != "mock"):
        if payload.provider_name.lower() == "mock":
            effective_key = "mock-key"
        else:
            key_stmt = select(WorkspaceApiKey).where(
                WorkspaceApiKey.workspace_id == workspace.id,
                WorkspaceApiKey.provider == payload.provider_name.lower(),
            )
            key_record = (await db.execute(key_stmt)).scalar_one_or_none()
            if key_record:
                try:
                    effective_key = decrypt_api_key(key_record.encrypted_key)
                except Exception:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to decrypt stored provider API key. Please re-register your key in the BYOK tab.",
                    )
            else:
                env_fallback = os.getenv(f"{payload.provider_name.upper()}_API_KEY")
                if env_fallback:
                    effective_key = env_fallback
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"No API key configured for provider '{payload.provider_name}'. Please add your API key in the 'API Keys (BYOK)' tab or pass it directly.",
                    )

    try:
        provider = ProviderFactory.create(payload.provider_name, api_key=effective_key, model=payload.model_name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to instantiate provider: {str(exc)}")

    engine = EvaluationEngine([ExactMatchEvaluator(), HitRateEvaluator(), LatencyTokenEvaluator()])

    dataset_items_data = [
        {
            "id": item.id,
            "query": item.query,
            "expected_output": item.expected_output,
            "contexts": item.contexts or [],
        }
        for item in dataset.items
    ]
    total_samples = len(dataset_items_data)

    async def event_generator():
        factory = get_session_factory()
        async with factory() as stream_db:
            try:
                experiment = Experiment(
                    name=payload.name,
                    description=payload.description,
                    dataset_id=payload.dataset_id,
                    workspace_id=workspace.id,
                    provider_name=payload.provider_name,
                    model_name=payload.model_name,
                    status="RUNNING",
                )
                stream_db.add(experiment)
                await stream_db.flush()

                start_event = StreamStartData(
                    experiment_id=experiment.id,
                    experiment_name=experiment.name,
                    total_samples=total_samples,
                    provider_name=payload.provider_name,
                    model_name=payload.model_name,
                    dataset_name=dataset.name,
                )
                yield f"event: started\ndata: {start_event.model_dump_json()}\n\n"

                total_latency = 0.0
                total_cost = 0.0
                total_tokens = 0
                successful_samples = 0
                failed_samples = 0
                quality_scores = []

                for idx, ds_item in enumerate(dataset_items_data, start=1):
                    try:
                        async with trace_async_run(
                            name=f"{payload.provider_name.capitalize()} - {payload.model_name or 'default'}",
                            run_type="llm",
                            inputs={"query": ds_item["query"], "dataset_id": str(payload.dataset_id)},
                            metadata={
                                "experiment_name": payload.name,
                                "provider": payload.provider_name,
                                "model": payload.model_name or "default",
                                "dataset_item_id": str(ds_item["id"]),
                                "workspace": workspace.name,
                            },
                        ) as trace_outputs:
                            gen_res = await provider.generate(ds_item["query"])
                            eval_dict = engine.evaluate_sample(
                                query=ds_item["query"],
                                response=gen_res.generated_text,
                                expected_output=ds_item["expected_output"],
                                retrieved_contexts=ds_item["contexts"],
                                ground_truth_contexts=ds_item["contexts"],
                                latency_ms=gen_res.latency_ms,
                                total_tokens=gen_res.total_tokens,
                            )
                            metrics_payload = {
                                k: {"score": v.score, "passed": v.passed, "reason": v.reason}
                                for k, v in eval_dict.items()
                            }

                            trace_outputs["output"] = gen_res.generated_text
                            trace_outputs["metrics"] = {k: v["score"] for k, v in metrics_payload.items()}
                            trace_outputs["latency_ms"] = gen_res.latency_ms
                            trace_outputs["total_tokens"] = gen_res.total_tokens
                            trace_outputs["cost_usd"] = gen_res.cost_usd

                            exp_item = ExperimentItem(
                                experiment_id=experiment.id,
                                dataset_item_id=ds_item["id"],
                                query=ds_item["query"],
                                response=gen_res.generated_text,
                                expected_output=ds_item["expected_output"],
                                metrics=metrics_payload,
                                latency_ms=gen_res.latency_ms,
                                total_tokens=gen_res.total_tokens,
                                cost_usd=gen_res.cost_usd,
                                status="SUCCESS",
                            )

                            total_latency += gen_res.latency_ms
                            total_cost += gen_res.cost_usd
                            total_tokens += gen_res.total_tokens
                            successful_samples += 1

                            sample_quality = [
                                v.score
                                for k, v in eval_dict.items()
                                if "latency" not in k.lower()
                                and "token" not in k.lower()
                                and "cost" not in k.lower()
                            ]
                            if sample_quality:
                                quality_scores.append(sum(sample_quality) / len(sample_quality))

                            passed = all(v.passed for v in eval_dict.values())
                            snippet = (
                                gen_res.generated_text[:140] + "..."
                                if len(gen_res.generated_text) > 140
                                else gen_res.generated_text
                            )

                            sample_event = StreamSampleData(
                                sample_index=idx,
                                total_samples=total_samples,
                                query=ds_item["query"],
                                response_snippet=snippet,
                                latency_ms=round(gen_res.latency_ms, 2),
                                total_tokens=gen_res.total_tokens,
                                cost_usd=round(gen_res.cost_usd, 6),
                                metrics={k: v.score for k, v in eval_dict.items()},
                                passed=passed,
                                progress_pct=round((idx / total_samples) * 100.0, 1),
                            )
                            yield f"event: sample_completed\ndata: {sample_event.model_dump_json()}\n\n"

                    except Exception as item_err:
                        failed_samples += 1
                        exp_item = ExperimentItem(
                            experiment_id=experiment.id,
                            dataset_item_id=ds_item["id"],
                            query=ds_item["query"],
                            response="",
                            expected_output=ds_item["expected_output"],
                            metrics={},
                            status="FAILED",
                            error_message=str(item_err),
                        )
                        err_event = StreamErrorData(
                            error_message=str(item_err),
                            sample_index=idx,
                            experiment_id=experiment.id,
                        )
                        yield f"event: error\ndata: {err_event.model_dump_json()}\n\n"

                    stream_db.add(exp_item)
                    await stream_db.flush()

                experiment.status = "COMPLETED"
                await stream_db.commit()

                composite_avg = (
                    round(sum(quality_scores) / len(quality_scores), 4)
                    if quality_scores
                    else 0.0
                )
                avg_latency = (
                    round(total_latency / successful_samples, 2)
                    if successful_samples
                    else 0.0
                )
                avg_tokens = (
                    int(total_tokens / successful_samples)
                    if successful_samples
                    else 0
                )

                complete_event = StreamCompleteData(
                    experiment_id=experiment.id,
                    experiment_name=experiment.name,
                    total_samples=total_samples,
                    successful_samples=successful_samples,
                    failed_samples=failed_samples,
                    composite_score=composite_avg,
                    avg_latency_ms=avg_latency,
                    avg_tokens=avg_tokens,
                    total_cost_usd=round(total_cost, 6),
                    status="SUCCESS",
                )
                yield f"event: completed\ndata: {complete_event.model_dump_json()}\n\n"

            except Exception as stream_err:
                await stream_db.rollback()
                err_event = StreamErrorData(
                    error_message=f"Stream execution failed: {str(stream_err)}"
                )
                yield f"event: error\ndata: {err_event.model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("", response_model=List[ExperimentResponse])
async def list_experiments(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    """List all evaluation experiments belonging to the active workspace."""
    stmt = (
        select(Experiment)
        .where(Experiment.workspace_id == workspace.id)
        .order_by(Experiment.created_at.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/analytics/pareto", response_model=ParetoAnalyticsResponse)
async def get_pareto_analytics(
    candidate_id: Optional[uuid.UUID] = Query(default=None, description="Optional candidate experiment ID to compare against baseline"),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Compute Pareto frontier (Quality vs Latency/Cost), Radar comparison, and historical quality trends for workspace."""
    stmt = (
        select(Experiment)
        .where(
            Experiment.workspace_id == workspace.id,
            Experiment.status == "COMPLETED"
        )
        .order_by(Experiment.created_at.asc())
    )
    res = await db.execute(stmt)
    experiments = list(res.scalars().all())

    return calculate_pareto_frontier(experiments, candidate_id=candidate_id)


@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(
    experiment_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve an experiment run by ID within the active workspace."""
    stmt = select(Experiment).where(
        Experiment.id == experiment_id,
        Experiment.workspace_id == workspace.id,
    )
    experiment = (await db.execute(stmt)).scalar_one_or_none()
    if not experiment:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found in active workspace.")
    return experiment


@router.post("/{experiment_id}/set-baseline", response_model=ExperimentResponse)
async def set_baseline(
    experiment_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    """Mark experiment as the active baseline for its dataset within the active workspace."""
    stmt = select(Experiment).where(
        Experiment.id == experiment_id,
        Experiment.workspace_id == workspace.id,
    )
    experiment = (await db.execute(stmt)).scalar_one_or_none()
    if not experiment:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found in active workspace.")

    clear_stmt = select(Experiment).where(
        Experiment.dataset_id == experiment.dataset_id,
        Experiment.workspace_id == workspace.id,
        Experiment.is_baseline.is_(True),
    )
    existing_baselines = (await db.execute(clear_stmt)).scalars().all()
    for b in existing_baselines:
        b.is_baseline = False

    experiment.is_baseline = True
    await db.commit()
    await db.refresh(experiment)
    return experiment


def _get_avg_metrics(exp: Experiment) -> dict[str, float]:
    sums: dict[str, float] = {}
    counts: dict[str, int] = {}
    for item in exp.items:
        for k, v in item.metrics.items():
            sums[k] = sums.get(k, 0.0) + v.get("score", 0.0)
            counts[k] = counts.get(k, 0) + 1
    return {k: round(sums[k] / counts[k], 4) for k in sums if counts[k] > 0}


@router.get("/{experiment_id}/compare", response_model=ComparisonDelta)
async def compare_experiment(
    experiment_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    """Compare candidate experiment against the active baseline within the active workspace."""
    stmt = select(Experiment).where(
        Experiment.id == experiment_id,
        Experiment.workspace_id == workspace.id,
    )
    candidate = (await db.execute(stmt)).scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found in active workspace.")

    base_stmt = select(Experiment).where(
        Experiment.dataset_id == candidate.dataset_id,
        Experiment.workspace_id == workspace.id,
        Experiment.is_baseline.is_(True),
    )
    baseline = (await db.execute(base_stmt)).scalar_one_or_none()
    if not baseline:
        raise HTTPException(status_code=400, detail="No active baseline set for this dataset.")

    cand_avg = _get_avg_metrics(candidate)
    base_avg = _get_avg_metrics(baseline)

    deltas = {}
    all_keys = set(cand_avg.keys()).union(base_avg.keys())
    for k in all_keys:
        c_score = cand_avg.get(k, 0.0)
        b_score = base_avg.get(k, 0.0)
        deltas[k] = {
            "candidate": c_score,
            "baseline": b_score,
            "delta": round(c_score - b_score, 4)
        }

    return ComparisonDelta(
        candidate_experiment_id=candidate.id,
        baseline_experiment_id=baseline.id,
        candidate_name=candidate.name,
        baseline_name=baseline.name,
        metric_deltas=deltas
    )


@router.get("/{experiment_id}/check-regression", response_model=RegressionReport)
async def check_regression(
    experiment_id: uuid.UUID,
    tolerance: float = Query(default=0.02, ge=0.0, le=1.0, description="Max allowed score drop"),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    """Evaluate candidate experiment against active baseline for quality regressions within workspace."""
    stmt = select(Experiment).where(
        Experiment.id == experiment_id,
        Experiment.workspace_id == workspace.id,
    )
    candidate = (await db.execute(stmt)).scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found in active workspace.")

    base_stmt = select(Experiment).where(
        Experiment.dataset_id == candidate.dataset_id,
        Experiment.workspace_id == workspace.id,
        Experiment.is_baseline.is_(True),
    )
    baseline = (await db.execute(base_stmt)).scalar_one_or_none()
    if not baseline:
        raise HTTPException(status_code=400, detail="No active baseline set for this dataset.")

    cand_avg = _get_avg_metrics(candidate)
    base_avg = _get_avg_metrics(baseline)

    detector = RegressionDetector(tolerance=tolerance)
    async with trace_async_run(
        name=f"CI Regression Gate - {candidate.name}",
        run_type="chain",
        inputs={
            "candidate_name": candidate.name,
            "candidate_metrics": cand_avg,
            "baseline_metrics": base_avg,
            "tolerance": tolerance,
        },
        metadata={"candidate_id": str(candidate.id), "baseline_id": str(baseline.id)},
    ) as trace_outputs:
        report = detector.detect_regression(candidate_metrics=cand_avg, baseline_metrics=base_avg)
        trace_outputs["has_regression"] = report.has_regression
        trace_outputs["regressed_metrics"] = report.regressed_metrics
        return report


@router.delete("/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experiment(
    experiment_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    """Delete an experiment run belonging to the active workspace."""
    stmt = select(Experiment).where(
        Experiment.id == experiment_id,
        Experiment.workspace_id == workspace.id,
    )
    experiment = (await db.execute(stmt)).scalar_one_or_none()
    if not experiment:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found in active workspace.")
    await db.delete(experiment)
    await db.commit()
    return None
