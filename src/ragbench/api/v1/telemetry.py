"""REST API Endpoints for Production Traffic Shadowing and Golden Set Harvester."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ragbench.core.rbac import (
    AuthContext,
    get_auth_context,
    require_evaluator,
    require_viewer,
)
from ragbench.db.session import get_db
from ragbench.models.traffic import ShadowTrafficSample
from ragbench.schemas.traffic import (
    GoldenSetPromotionRequest,
    GoldenSetPromotionResponse,
    TrafficSampleBatchIngest,
    TrafficSampleIngest,
    TrafficSampleListResponse,
    TrafficSampleResponse,
    TrafficStatsResponse,
)
from ragbench.services.harvester import (
    analyze_traffic_sample,
    promote_samples_to_dataset,
)

router = APIRouter(prefix="/telemetry", tags=["Production Traffic Shadowing & Harvester"])


@router.post("/sample", response_model=TrafficSampleResponse, status_code=status.HTTP_201_CREATED)
async def ingest_traffic_sample(
    payload: TrafficSampleIngest,
    ctx: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    """Ingest a background production traffic sample and run automated edge-case analysis."""
    is_flagged, flag_reason = analyze_traffic_sample(payload)

    sample = ShadowTrafficSample(
        workspace_id=ctx.workspace.id,
        session_id=payload.session_id,
        user_query=payload.user_query,
        model_response=payload.model_response,
        retrieved_contexts=payload.retrieved_contexts or [],
        latency_ms=payload.latency_ms,
        token_count=payload.token_count,
        cost_usd=payload.cost_usd,
        provider=payload.provider,
        model=payload.model,
        guardrails_triggered=payload.guardrails_triggered or False,
        guardrails_violations=payload.guardrails_violations or [],
        confidence_score=payload.confidence_score,
        is_flagged=is_flagged,
        flag_reason=flag_reason,
        is_promoted=False,
        sample_metadata=payload.sample_metadata or {},
    )
    db.add(sample)
    await db.commit()
    await db.refresh(sample)

    return sample


@router.post("/batch", response_model=List[TrafficSampleResponse], status_code=status.HTTP_201_CREATED)
async def ingest_batch_samples(
    payload: TrafficSampleBatchIngest,
    ctx: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    """Batch ingest production samples from live microservices or background flushes."""
    created_samples: List[ShadowTrafficSample] = []
    for item in payload.samples:
        is_flagged, flag_reason = analyze_traffic_sample(item)
        sample = ShadowTrafficSample(
            workspace_id=ctx.workspace.id,
            session_id=item.session_id,
            user_query=item.user_query,
            model_response=item.model_response,
            retrieved_contexts=item.retrieved_contexts or [],
            latency_ms=item.latency_ms,
            token_count=item.token_count,
            cost_usd=item.cost_usd,
            provider=item.provider,
            model=item.model,
            guardrails_triggered=item.guardrails_triggered or False,
            guardrails_violations=item.guardrails_violations or [],
            confidence_score=item.confidence_score,
            is_flagged=is_flagged,
            flag_reason=flag_reason,
            is_promoted=False,
            sample_metadata=item.sample_metadata or {},
        )
        db.add(sample)
        created_samples.append(sample)

    await db.commit()
    for s in created_samples:
        await db.refresh(s)

    return created_samples


@router.get("/samples", response_model=TrafficSampleListResponse)
async def list_traffic_samples(
    flagged_only: bool = Query(default=False, description="Filter only flagged anomalies"),
    flag_reason: Optional[str] = Query(default=None, description="Filter by anomaly flag reason"),
    promoted: Optional[bool] = Query(default=None, description="Filter by promotion status"),
    provider: Optional[str] = Query(default=None, description="Filter by provider"),
    search: Optional[str] = Query(default=None, description="Search in user query"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=50, ge=1, le=200, description="Items per page"),
    ctx: AuthContext = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """List shadowed production traffic samples with rich anomaly and metadata filtering."""
    stmt = select(ShadowTrafficSample).where(ShadowTrafficSample.workspace_id == ctx.workspace.id)

    if flagged_only:
        stmt = stmt.where(ShadowTrafficSample.is_flagged.is_(True))
    if flag_reason and flag_reason != "ALL":
        stmt = stmt.where(ShadowTrafficSample.flag_reason == flag_reason)
    if promoted is not None:
        stmt = stmt.where(ShadowTrafficSample.is_promoted.is_(promoted))
    if provider and provider != "ALL":
        stmt = stmt.where(ShadowTrafficSample.provider == provider)
    if search:
        stmt = stmt.where(ShadowTrafficSample.user_query.ilike(f"%{search}%"))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    flagged_count_stmt = select(func.count()).where(
        ShadowTrafficSample.workspace_id == ctx.workspace.id,
        ShadowTrafficSample.is_flagged.is_(True),
    )
    flagged_total = (await db.execute(flagged_count_stmt)).scalar() or 0

    offset = (page - 1) * limit
    paged_stmt = stmt.order_by(ShadowTrafficSample.created_at.desc(), ShadowTrafficSample.id.desc()).offset(offset).limit(limit)
    records = (await db.execute(paged_stmt)).scalars().all()

    return TrafficSampleListResponse(
        items=[TrafficSampleResponse.model_validate(r) for r in records],
        total=total,
        page=page,
        limit=limit,
        flagged_count=flagged_total,
    )


@router.get("/stats", response_model=TrafficStatsResponse)
async def get_traffic_stats(
    ctx: AuthContext = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve statistical distribution, anomaly rates, and P95 latency across shadowed traffic."""
    stmt = select(ShadowTrafficSample).where(ShadowTrafficSample.workspace_id == ctx.workspace.id)
    records = (await db.execute(stmt)).scalars().all()

    total = len(records)
    if total == 0:
        return TrafficStatsResponse(
            total_samples=0,
            flagged_count=0,
            anomaly_rate_percent=0.0,
            promoted_count=0,
            reasons_breakdown={},
            provider_breakdown={},
            avg_latency_ms=0.0,
            p95_latency_ms=0.0,
        )

    flagged = [r for r in records if r.is_flagged]
    promoted = [r for r in records if r.is_promoted]

    reasons: dict[str, int] = {}
    for r in flagged:
        if r.flag_reason:
            reasons[r.flag_reason] = reasons.get(r.flag_reason, 0) + 1

    providers: dict[str, int] = {}
    latencies: list[float] = []
    for r in records:
        if r.provider:
            providers[r.provider] = providers.get(r.provider, 0) + 1
        if r.latency_ms is not None:
            latencies.append(r.latency_ms)

    latencies.sort()
    avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
    p95_lat = latencies[int(len(latencies) * 0.95)] if latencies else 0.0

    return TrafficStatsResponse(
        total_samples=total,
        flagged_count=len(flagged),
        anomaly_rate_percent=round((len(flagged) / total) * 100.0, 2),
        promoted_count=len(promoted),
        reasons_breakdown=reasons,
        provider_breakdown=providers,
        avg_latency_ms=round(avg_lat, 2),
        p95_latency_ms=round(p95_lat, 2),
    )


@router.post("/promote", response_model=GoldenSetPromotionResponse)
async def promote_to_golden_set(
    payload: GoldenSetPromotionRequest,
    ctx: AuthContext = Depends(require_evaluator),
    db: AsyncSession = Depends(get_db),
):
    """1-Click promotion converting selected production edge cases into permanent Golden Benchmark items."""
    return await promote_samples_to_dataset(
        db=db,
        workspace_id=ctx.workspace.id,
        request=payload,
        user_id=ctx.user_id,
        user_email=ctx.user_email,
        client_ip=ctx.client_ip,
    )


@router.delete("/samples/{sample_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sample(
    sample_id: str,
    ctx: AuthContext = Depends(require_evaluator),
    db: AsyncSession = Depends(get_db),
):
    """Delete a shadowed traffic sample from the workspace database."""
    stmt = select(ShadowTrafficSample).where(
        ShadowTrafficSample.id == sample_id,
        ShadowTrafficSample.workspace_id == ctx.workspace.id,
    )
    sample = (await db.execute(stmt)).scalar_one_or_none()
    if not sample:
        raise HTTPException(status_code=404, detail="Traffic sample not found")

    await db.delete(sample)
    await db.commit()
