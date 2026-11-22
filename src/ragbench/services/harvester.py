"""Production Traffic Shadowing and Golden Set Harvester service."""
import re
import uuid
from typing import List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ragbench.core.audit import record_audit_event
from ragbench.core.logging import logger
from ragbench.models.dataset import Dataset, DatasetItem
from ragbench.models.traffic import ShadowTrafficSample
from ragbench.schemas.traffic import (
    GoldenSetPromotionRequest,
    GoldenSetPromotionResponse,
    TrafficSampleIngest,
)

ERROR_INDICATORS = re.compile(
    r"(rate limit|429 too many|500 internal server|503 service unavailable|context_length_exceeded|overloaded)",
    re.IGNORECASE,
)


def analyze_traffic_sample(sample: TrafficSampleIngest) -> Tuple[bool, Optional[str]]:
    """Heuristic rule-engine flagging production edge cases, anomalies, and quality drop-offs."""
    # 1. Guardrail intervention
    if sample.guardrails_triggered:
        return True, "GUARDRAIL_INTERCEPTED"

    # 2. Severe latency anomaly (>= 2500 ms)
    if sample.latency_ms is not None and sample.latency_ms >= 2500.0:
        return True, "HIGH_LATENCY"

    # 3. Low model confidence (< 0.65)
    if sample.confidence_score is not None and sample.confidence_score < 0.65:
        return True, "LOW_CONFIDENCE"

    # 4. Empty or trivially truncated model generation
    if not sample.model_response or len(sample.model_response.strip()) < 5:
        return True, "EMPTY_RESPONSE"

    # 5. Upstream provider error leaked into output text
    if sample.model_response and ERROR_INDICATORS.search(sample.model_response):
        return True, "ERROR_OUTPUT"

    return False, None


async def promote_samples_to_dataset(
    db: AsyncSession,
    workspace_id: str,
    request: GoldenSetPromotionRequest,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    client_ip: Optional[str] = None,
) -> GoldenSetPromotionResponse:
    """Promote selected flagged production edge cases into permanent Golden Benchmark Dataset items."""
    stmt = select(ShadowTrafficSample).where(
        ShadowTrafficSample.workspace_id == workspace_id,
        ShadowTrafficSample.id.in_(request.sample_ids),
    )
    samples: List[ShadowTrafficSample] = (await db.execute(stmt)).scalars().all()

    if not samples:
        raise HTTPException(status_code=404, detail="No matching traffic samples found in workspace.")

    created_new = False
    if request.target_dataset_id:
        target_uuid = uuid.UUID(request.target_dataset_id) if isinstance(request.target_dataset_id, str) else request.target_dataset_id
        ds_stmt = select(Dataset).where(
            Dataset.id == target_uuid,
            Dataset.workspace_id == workspace_id,
        )
        dataset = (await db.execute(ds_stmt)).scalar_one_or_none()
        if not dataset:
            raise HTTPException(status_code=404, detail="Target dataset not found in active workspace.")
    else:
        created_new = True
        dataset_name = request.new_dataset_name or f"Production Harvest {samples[0].created_at.strftime('%Y-%m-%d') if samples[0].created_at else ''}"
        dataset = Dataset(
            name=dataset_name,
            description=request.new_dataset_description or "Curated edge cases promoted from production traffic shadowing",
            version="1.0.0",
            workspace_id=workspace_id,
        )
        db.add(dataset)
        await db.flush()
        await db.refresh(dataset)

    # Convert samples to DatasetItems
    promoted_ids: List[str] = []
    for s in samples:
        item = DatasetItem(
            dataset_id=dataset.id,
            query=s.user_query,
            expected_output=s.model_response or "",
            contexts=s.retrieved_contexts or [],
            item_metadata={
                "source": "shadow_telemetry",
                "flag_reason": s.flag_reason,
                "original_sample_id": s.id,
                "latency_ms": s.latency_ms,
                "confidence_score": s.confidence_score,
                "provider": s.provider,
                "model": s.model,
            },
        )
        db.add(item)
        s.is_promoted = True
        s.promoted_to_dataset_id = dataset.id if isinstance(dataset.id, uuid.UUID) else uuid.UUID(str(dataset.id))
        promoted_ids.append(s.id)

    await db.flush()

    # Record tamper-evident audit trail
    await record_audit_event(
        db,
        workspace_id=workspace_id,
        action="GOLDEN_SET_PROMOTED",
        resource_type="dataset",
        resource_id=str(dataset.id),
        details={
            "dataset_name": dataset.name,
            "promoted_count": len(promoted_ids),
            "sample_ids": promoted_ids,
        },
        user_id=user_id,
        user_email=user_email,
        ip_address=client_ip,
    )
    await db.commit()
    logger.info(f"[Harvester] Promoted {len(promoted_ids)} samples to dataset '{dataset.name}' ({dataset.id})")

    return GoldenSetPromotionResponse(
        dataset_id=str(dataset.id),
        dataset_name=dataset.name,
        promoted_count=len(promoted_ids),
        created_new=created_new,
        promoted_sample_ids=promoted_ids,
        message=f"Successfully promoted {len(promoted_ids)} production edge cases to '{dataset.name}'.",
    )
