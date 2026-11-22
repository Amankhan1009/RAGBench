"""Comprehensive tests for Enterprise RBAC and Tamper-Evident Audit Logging (v3.5)."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update

from ragbench.core.audit import compute_audit_hash, record_audit_event, verify_audit_log_chain
from ragbench.core.jwt import create_access_token, hash_password
from ragbench.db.base import Base
from ragbench.db.session import get_engine, get_session_factory
from ragbench.main import app
from ragbench.models.audit import AuditLog
from ragbench.models.user import User
from ragbench.models.workspace import Workspace


@pytest.fixture(autouse=True)
async def setup_test_db():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.mark.asyncio
async def test_cryptographic_audit_hash_chain():
    """Verify that SHA-256 audit chaining produces deterministic and verifiable hashes."""
    prev_hash = "GENESIS"
    workspace_id = str(uuid.uuid4())
    ts = "2026-11-22T12:00:00Z"

    hash1 = compute_audit_hash(
        prev_hash=prev_hash,
        workspace_id=workspace_id,
        action="DATASET_CREATED",
        resource_type="dataset",
        resource_id="ds-1",
        user_email="admin@corp.internal",
        timestamp_str=ts,
        details={"name": "Golden Set", "count": 10},
    )
    assert len(hash1) == 64

    # Hash of second record depends on hash1
    hash2 = compute_audit_hash(
        prev_hash=hash1,
        workspace_id=workspace_id,
        action="BASELINE_SET",
        resource_type="experiment",
        resource_id="exp-1",
        user_email="admin@corp.internal",
        timestamp_str=ts,
        details={"experiment": "Llama-3.3-eval"},
    )
    assert len(hash2) == 64
    assert hash1 != hash2


@pytest.mark.asyncio
async def test_audit_event_recording_and_verification():
    """Test creating real audit log records and verifying chain integrity."""
    session_factory = get_session_factory()
    workspace_id = f"ws-{uuid.uuid4()}"

    async with session_factory() as db:
        # Create workspace
        ws = Workspace(id=workspace_id, name="Security Test Workspace", api_key=f"key-{uuid.uuid4()}")
        db.add(ws)
        await db.flush()

        # Add 3 chained audit events
        await record_audit_event(
            db,
            workspace_id=workspace_id,
            action="DATASET_CREATED",
            resource_type="dataset",
            resource_id="ds-100",
            details={"samples": 5},
            user_email="evaluator@corp.internal",
        )
        await record_audit_event(
            db,
            workspace_id=workspace_id,
            action="API_KEY_REGISTERED",
            resource_type="api_key",
            resource_id="key-100",
            details={"provider": "groq"},
            user_email="admin@corp.internal",
        )
        await record_audit_event(
            db,
            workspace_id=workspace_id,
            action="GUARDRAIL_POLICY_UPDATED",
            resource_type="guardrail",
            details={"enabled": True},
            user_email="admin@corp.internal",
        )
        await db.commit()

    # Verify chain
    async with session_factory() as db:
        report = await verify_audit_log_chain(db, workspace_id)
        assert report["total_records"] == 3
        assert report["verified_records"] == 3
        assert report["is_valid"] is True
        assert report["chain_status"] == "SECURE"
        assert len(report["tampered_records"]) == 0


@pytest.mark.asyncio
async def test_tamper_detection_on_altered_audit_log():
    """Verify that tampering with an audit log record payload immediately causes integrity failure."""
    session_factory = get_session_factory()
    workspace_id = f"ws-{uuid.uuid4()}"

    async with session_factory() as db:
        ws = Workspace(id=workspace_id, name="Tamper Test WS", api_key=f"key-{uuid.uuid4()}")
        db.add(ws)
        await db.flush()

        rec1 = await record_audit_event(
            db,
            workspace_id=workspace_id,
            action="DATASET_CREATED",
            resource_type="dataset",
            resource_id="ds-1",
            details={"items": 10},
        )
        await record_audit_event(
            db,
            workspace_id=workspace_id,
            action="BASELINE_SET",
            resource_type="experiment",
            resource_id="exp-1",
            details={"score": 0.95},
        )
        await db.commit()

        target_id = rec1.id

    # Malicious direct DB alteration: change details
    async with session_factory() as db:
        stmt = (
            update(AuditLog)
            .where(AuditLog.id == target_id)
            .values(details={"items": 99999})  # Falsified data
        )
        await db.execute(stmt)
        await db.commit()

    # Verification must flag the tampering
    async with session_factory() as db:
        report = await verify_audit_log_chain(db, workspace_id)
        assert report["is_valid"] is False
        assert report["chain_status"] == "COMPROMISED"
        assert len(report["tampered_records"]) > 0
        assert report["tampered_records"][0]["record_id"] == target_id


@pytest.mark.asyncio
async def test_rbac_user_registration_and_member_management():
    """Test role assignment, invitation, role updates, and safety guards via REST API."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Register Admin user
        admin_email = f"admin_{uuid.uuid4().hex[:6]}@enterprise.com"
        reg_res = await ac.post("/api/v1/auth/register", json={
            "email": admin_email,
            "password": "Password123!",
            "name": "Super Admin",
        })
        assert reg_res.status_code == 201
        admin_data = reg_res.json()
        admin_token = admin_data["access_token"]
        assert admin_data["user"]["role"] == "admin"
        admin_id = admin_data["user"]["id"]

        headers_admin = {"Authorization": f"Bearer {admin_token}"}

        # 2. Admin invites an Evaluator
        eval_email = f"eval_{uuid.uuid4().hex[:6]}@enterprise.com"
        invite_res = await ac.post("/api/v1/workspaces/members", headers=headers_admin, json={
            "email": eval_email,
            "name": "Jane Evaluator",
            "role": "evaluator",
            "password": "Password123!",
        })
        assert invite_res.status_code == 201
        eval_user = invite_res.json()
        assert eval_user["role"] == "evaluator"
        eval_id = eval_user["id"]

        # 3. Admin invites a Viewer
        viewer_email = f"viewer_{uuid.uuid4().hex[:6]}@enterprise.com"
        viewer_res = await ac.post("/api/v1/workspaces/members", headers=headers_admin, json={
            "email": viewer_email,
            "name": "Auditor Bob",
            "role": "viewer",
            "password": "Password123!",
        })
        assert viewer_res.status_code == 201
        viewer_user = viewer_res.json()
        assert viewer_user["role"] == "viewer"
        assert viewer_user["id"]

        # 4. List members
        members_res = await ac.get("/api/v1/workspaces/members", headers=headers_admin)
        assert members_res.status_code == 200
        members = members_res.json()
        assert len(members) == 3

        # 5. Login as Viewer
        login_viewer = await ac.post("/api/v1/auth/login", json={
            "email": viewer_email,
            "password": "Password123!",
        })
        assert login_viewer.status_code == 200
        viewer_token = login_viewer.json()["access_token"]
        headers_viewer = {"Authorization": f"Bearer {viewer_token}"}

        # 6. Viewer tries to add member -> must be 403 Forbidden!
        forbidden_invite = await ac.post("/api/v1/workspaces/members", headers=headers_viewer, json={
            "email": "hacker@evil.com",
            "role": "admin",
            "password": "Password123!",
        })
        assert forbidden_invite.status_code == 403

        # 7. Viewer tries to register API key -> must be 403 Forbidden!
        forbidden_key = await ac.post("/api/v1/auth/keys", headers=headers_viewer, json={
            "provider": "openai",
            "api_key": "sk-test-secret-key-12345",
        })
        assert forbidden_key.status_code == 403

        # 8. Admin updates Evaluator to Admin
        update_res = await ac.patch(f"/api/v1/workspaces/members/{eval_id}", headers=headers_admin, json={
            "role": "admin",
        })
        assert update_res.status_code == 200
        assert update_res.json()["role"] == "admin"

        # 9. Safety check: Cannot demote the last remaining admin (if only one)
        # First demote eval_user back to evaluator
        await ac.patch(f"/api/v1/workspaces/members/{eval_id}", headers=headers_admin, json={
            "role": "evaluator",
        })
        # Now admin tries to demote themselves (the only admin left)
        bad_demote = await ac.patch(f"/api/v1/workspaces/members/{admin_id}", headers=headers_admin, json={
            "role": "viewer",
        })
        assert bad_demote.status_code == 400
        assert "only remaining Admin" in bad_demote.json()["detail"]


@pytest.mark.asyncio
async def test_audit_api_logs_and_verification_endpoints():
    """Test GET /api/v1/audit/logs, /api/v1/audit/verify, and /api/v1/audit/stats."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        admin_email = f"auditor_{uuid.uuid4().hex[:6]}@enterprise.com"
        reg_res = await ac.post("/api/v1/auth/register", json={
            "email": admin_email,
            "password": "Password123!",
            "name": "Audit Officer",
        })
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Query audit logs
        logs_res = await ac.get("/api/v1/audit/logs", headers=headers)
        assert logs_res.status_code == 200
        log_data = logs_res.json()
        assert "items" in log_data
        assert log_data["total"] >= 2  # WORKSPACE_CREATED & USER_REGISTERED

        # Verify integrity
        verify_res = await ac.get("/api/v1/audit/verify", headers=headers)
        assert verify_res.status_code == 200
        verify_data = verify_res.json()
        assert verify_data["is_valid"] is True
        assert verify_data["chain_status"] == "SECURE"

        # Query stats
        stats_res = await ac.get("/api/v1/audit/stats", headers=headers)
        assert stats_res.status_code == 200
        stats_data = stats_res.json()
        assert stats_data["total_events"] >= 2
        assert stats_data["chain_status"] == "SECURE"
