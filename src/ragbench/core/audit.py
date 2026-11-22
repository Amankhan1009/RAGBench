"""Cryptographic tamper-evident audit logging engine with SHA-256 hash chaining."""
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ragbench.core.logging import logger
from ragbench.models.audit import AuditLog


def canonical_json(data: Optional[Dict[str, Any]]) -> str:
    """Produce deterministic canonical JSON string with sorted keys."""
    if not data:
        return "{}"
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def format_timestamp(dt: Optional[datetime]) -> str:
    """Standardize datetime to a deterministic timezone-neutral string for hashing."""
    if not dt:
        return ""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")


def compute_audit_hash(
    prev_hash: str,
    workspace_id: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str],
    user_email: Optional[str],
    timestamp_str: str,
    details: Optional[Dict[str, Any]],
) -> str:
    """Compute SHA-256 digest linking this entry to the previous record hash."""
    payload = (
        f"{prev_hash or 'GENESIS'}:"
        f"{workspace_id}:"
        f"{action}:"
        f"{resource_type}:"
        f"{resource_id or ''}:"
        f"{user_email or ''}:"
        f"{timestamp_str}:"
        f"{canonical_json(details)}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def record_audit_event(
    db: AsyncSession,
    workspace_id: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Append a tamper-evident audit log entry chained cryptographically to the prior entry."""
    try:
        # Fetch latest entry in workspace to retrieve parent hash
        stmt = (
            select(AuditLog)
            .where(AuditLog.workspace_id == workspace_id)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(1)
        )
        latest_record = (await db.execute(stmt)).scalar_one_or_none()
        prev_hash = latest_record.record_hash if (latest_record and latest_record.record_hash) else "GENESIS"

        now_utc = datetime.now(timezone.utc)
        record_id = str(uuid.uuid4())
        record_hash = compute_audit_hash(
            prev_hash=prev_hash,
            workspace_id=workspace_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_email=user_email,
            timestamp_str=format_timestamp(now_utc),
            details=details,
        )

        entry = AuditLog(
            id=record_id,
            workspace_id=workspace_id,
            user_id=user_id,
            user_email=user_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            created_at=now_utc,
            prev_hash=prev_hash,
            record_hash=record_hash,
        )
        db.add(entry)
        await db.flush()
        return entry
    except Exception as exc:
        logger.error(f"[Audit] Failed to record audit event '{action}': {exc}", exc_info=True)
        raise


async def verify_audit_log_chain(
    db: AsyncSession,
    workspace_id: str,
) -> Dict[str, Any]:
    """Verify cryptographic hash integrity across all historical audit entries for a workspace."""
    stmt = (
        select(AuditLog)
        .where(AuditLog.workspace_id == workspace_id)
        .order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
    )
    records = (await db.execute(stmt)).scalars().all()

    total = len(records)
    if total == 0:
        return {
            "total_records": 0,
            "verified_records": 0,
            "is_valid": True,
            "tampered_records": [],
            "chain_status": "SECURE",
            "message": "Audit chain is empty. 0 records to verify.",
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

    tampered: List[Dict[str, Any]] = []
    expected_prev = "GENESIS"

    for idx, rec in enumerate(records):
        prev_matches = (rec.prev_hash == expected_prev)
        ts_str = format_timestamp(rec.created_at)
        computed_hash = compute_audit_hash(
            prev_hash=rec.prev_hash or "GENESIS",
            workspace_id=rec.workspace_id,
            action=rec.action,
            resource_type=rec.resource_type,
            resource_id=rec.resource_id,
            user_email=rec.user_email,
            timestamp_str=ts_str,
            details=rec.details,
        )
        hash_matches = (computed_hash == rec.record_hash)

        if not prev_matches or not hash_matches:
            tampered.append({
                "record_id": rec.id,
                "index": idx,
                "action": rec.action,
                "prev_hash_matches": prev_matches,
                "hash_matches": hash_matches,
                "expected_hash": computed_hash,
                "recorded_hash": rec.record_hash,
            })

        expected_prev = rec.record_hash

    is_valid = (len(tampered) == 0)
    return {
        "total_records": total,
        "verified_records": total - len(tampered),
        "is_valid": is_valid,
        "tampered_records": tampered,
        "chain_status": "SECURE" if is_valid else "COMPROMISED",
        "message": (
            "All cryptographic audit log hashes verified successfully."
            if is_valid
            else f"Audit log tampering detected in {len(tampered)} records!"
        ),
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }
