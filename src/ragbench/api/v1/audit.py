"""Tamper-evident audit log querying, verification, and analytics endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ragbench.core.audit import verify_audit_log_chain
from ragbench.core.rbac import (
    AuthContext,
    require_viewer,
)
from ragbench.db.session import get_db
from ragbench.models.audit import AuditLog
from ragbench.schemas.audit import (
    AuditLogListResponse,
    AuditLogResponse,
    AuditStatsResponse,
    AuditVerificationResponse,
)

router = APIRouter(prefix="/audit", tags=["Tamper-Evident Audit Logging"])


@router.get("/logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    action: Optional[str] = Query(default=None, description="Filter by event action"),
    resource_type: Optional[str] = Query(default=None, description="Filter by resource type"),
    user_email: Optional[str] = Query(default=None, description="Filter by user email"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(default=50, ge=1, le=200, description="Items per page"),
    ctx: AuthContext = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve filtered, chronologically paginated audit log events for the current workspace."""
    stmt = select(AuditLog).where(AuditLog.workspace_id == ctx.workspace.id)

    if action:
        stmt = stmt.where(AuditLog.action == action.upper())
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type.lower())
    if user_email:
        stmt = stmt.where(AuditLog.user_email.ilike(f"%{user_email}%"))

    # Total count query
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Pagination & sorting
    offset = (page - 1) * limit
    paged_stmt = stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).offset(offset).limit(limit)
    records = (await db.execute(paged_stmt)).scalars().all()

    return AuditLogListResponse(
        items=[
            AuditLogResponse(
                id=r.id,
                workspace_id=r.workspace_id,
                user_id=r.user_id,
                user_email=r.user_email,
                action=r.action,
                resource_type=r.resource_type,
                resource_id=r.resource_id,
                details=r.details,
                ip_address=r.ip_address,
                created_at=r.created_at,
                prev_hash=r.prev_hash,
                record_hash=r.record_hash,
            )
            for r in records
        ],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/verify", response_model=AuditVerificationResponse)
async def verify_integrity(
    ctx: AuthContext = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """Run cryptographic SHA-256 chain verification across all workspace audit records."""
    report = await verify_audit_log_chain(db, ctx.workspace.id)
    return AuditVerificationResponse(**report)


@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_stats(
    ctx: AuthContext = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """Get high-level summary statistics of audit trail activity and current chain status."""
    stmt = select(AuditLog).where(AuditLog.workspace_id == ctx.workspace.id)
    records = (await db.execute(stmt)).scalars().all()

    events_by_action = {}
    events_by_resource = {}
    users = set()
    latest_ts = None

    for r in records:
        events_by_action[r.action] = events_by_action.get(r.action, 0) + 1
        events_by_resource[r.resource_type] = events_by_resource.get(r.resource_type, 0) + 1
        if r.user_email:
            users.add(r.user_email)
        if r.created_at and (latest_ts is None or r.created_at > latest_ts):
            latest_ts = r.created_at

    # Quick integrity status check
    verification = await verify_audit_log_chain(db, ctx.workspace.id)

    return AuditStatsResponse(
        total_events=len(records),
        events_by_action=events_by_action,
        events_by_resource=events_by_resource,
        unique_users=len(users),
        latest_event_at=latest_ts,
        chain_status=verification["chain_status"],
    )
