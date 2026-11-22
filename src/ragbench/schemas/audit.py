"""Pydantic schemas for tamper-evident audit logging and cryptographic verification."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AuditLogResponse(BaseModel):
    id: str
    workspace_id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime
    prev_hash: Optional[str] = None
    record_hash: str

    model_config = {"from_attributes": True}


class AuditVerificationTamperedItem(BaseModel):
    record_id: str
    index: int
    action: str
    prev_hash_matches: bool
    hash_matches: bool
    expected_hash: str
    recorded_hash: str


class AuditVerificationResponse(BaseModel):
    total_records: int
    verified_records: int
    is_valid: bool
    tampered_records: List[AuditVerificationTamperedItem] = []
    chain_status: str = Field(description="'SECURE' or 'COMPROMISED'")
    message: str
    verified_at: str


class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    limit: int


class AuditStatsResponse(BaseModel):
    total_events: int
    events_by_action: Dict[str, int]
    events_by_resource: Dict[str, int]
    unique_users: int
    latest_event_at: Optional[datetime] = None
    chain_status: str
