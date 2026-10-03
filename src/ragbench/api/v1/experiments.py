"""Experiment execution, baseline comparison, and regression detection REST API endpoints."""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ragbench.db.session import get_db
from ragbench.evaluators.deterministic import (
    ExactMatchEvaluator,
    HitRateEvaluator,
    LatencyTokenEvaluator,
)
from ragbench.evaluators.engine import EvaluationEngine
from ragbench.evaluators.regression import RegressionDetector, RegressionReport
from ragbench.models.dataset import Dataset
from ragbench.models.experiment import Experiment, ExperimentItem
from ragbench.providers.factory import ProviderFactory
from ragbench.schemas.experiment import (
    ComparisonDelta,
    ExperimentCreate,
    ExperimentResponse,
)

router = APIRouter(prefix="/experiments", tags=["Experiments"])


@router.post("", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_experiment(payload: ExperimentCreate, db: AsyncSession = Depends(get_db)):
    """Launch an evaluation experiment across dataset items."""
    stmt = select(Dataset).where(Dataset.id == payload.dataset_id)
    dataset = (await db.execute(stmt)).scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset '{payload.dataset_id}' not found.")

    try:
        provider = ProviderFactory.create(payload.provider_name, api_key=payload.api_key or "mock-key", model=payload.model_name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to instantiate provider: {str(exc)}")

    engine = EvaluationEngine([ExactMatchEvaluator(), HitRateEvaluator(), LatencyTokenEvaluator()])

    experiment = Experiment(
        name=payload.name,
        description=payload.description,
        dataset_id=payload.dataset_id,
        provider_name=payload.provider_name,
        model_name=payload.model_name,
        status="RUNNING"
    )
    db.add(experiment)
    await db.flush()

    for ds_item in dataset.items:
        try:
            gen_res = await provider.generate(ds_item.query)
            eval_dict = engine.evaluate_sample(
                query=ds_item.query,
                response=gen_res.generated_text,
                expected_output=ds_item.expected_output,
                retrieved_contexts=ds_item.contexts,
                ground_truth_contexts=ds_item.contexts,
                latency_ms=gen_res.latency_ms,
                total_tokens=gen_res.total_tokens
            )
            metrics_payload = {k: {"score": v.score, "passed": v.passed, "reason": v.reason} for k, v in eval_dict.items()}

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
                status="SUCCESS"
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

@router.get("", response_model=List[ExperimentResponse])
async def list_experiments(db: AsyncSession = Depends(get_db)):
    """List all evaluation experiments ordered by creation time."""
    stmt = select(Experiment).order_by(Experiment.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(experiment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Retrieve an experiment run by ID."""
    stmt = select(Experiment).where(Experiment.id == experiment_id)
    experiment = (await db.execute(stmt)).scalar_one_or_none()
    if not experiment:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found.")
    return experiment


@router.post("/{experiment_id}/set-baseline", response_model=ExperimentResponse)
async def set_baseline(experiment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Mark experiment as the active baseline for its dataset."""
    stmt = select(Experiment).where(Experiment.id == experiment_id)
    experiment = (await db.execute(stmt)).scalar_one_or_none()
    if not experiment:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found.")

    clear_stmt = select(Experiment).where(
        Experiment.dataset_id == experiment.dataset_id,
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
async def compare_experiment(experiment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Compare candidate experiment against the active baseline."""
    stmt = select(Experiment).where(Experiment.id == experiment_id)
    candidate = (await db.execute(stmt)).scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found.")

    base_stmt = select(Experiment).where(Experiment.dataset_id == candidate.dataset_id, Experiment.is_baseline.is_(True))
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
    db: AsyncSession = Depends(get_db)
):
    """Evaluate candidate experiment against active baseline for quality regressions."""
    stmt = select(Experiment).where(Experiment.id == experiment_id)
    candidate = (await db.execute(stmt)).scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found.")

    base_stmt = select(Experiment).where(
        Experiment.dataset_id == candidate.dataset_id,
        Experiment.is_baseline.is_(True),
    )
    baseline = (await db.execute(base_stmt)).scalar_one_or_none()
    if not baseline:
        raise HTTPException(status_code=400, detail="No active baseline set for this dataset.")

    cand_avg = _get_avg_metrics(candidate)
    base_avg = _get_avg_metrics(baseline)

    detector = RegressionDetector(tolerance=tolerance)
    return detector.detect_regression(candidate_metrics=cand_avg, baseline_metrics=base_avg)
