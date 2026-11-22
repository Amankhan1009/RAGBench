"""Workspace member management and Role-Based Access Control endpoints."""
import secrets
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ragbench.core.audit import record_audit_event
from ragbench.core.jwt import hash_password
from ragbench.core.rbac import (
    AuthContext,
    require_admin,
    require_viewer,
)
from ragbench.db.session import get_db
from ragbench.models.user import User
from ragbench.schemas.auth import (
    WorkspaceMemberInvite,
    WorkspaceMemberResponse,
    WorkspaceMemberUpdate,
)

router = APIRouter(prefix="/workspaces/members", tags=["Workspace RBAC & Team Management"])


@router.get("", response_model=List[WorkspaceMemberResponse])
async def list_workspace_members(
    ctx: AuthContext = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """List all members belonging to the active workspace."""
    stmt = (
        select(User)
        .where(User.workspace_id == ctx.workspace.id)
        .order_by(User.created_at.asc())
    )
    members = (await db.execute(stmt)).scalars().all()

    return [
        WorkspaceMemberResponse(
            id=m.id,
            email=m.email,
            name=m.name,
            role=m.role or "admin",
            workspace_id=m.workspace_id,
            created_at=m.created_at,
        )
        for m in members
    ]


@router.post("", response_model=WorkspaceMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_workspace_member(
    payload: WorkspaceMemberInvite,
    ctx: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Invite or add a new team member with an assigned role (Admin only)."""
    # Verify email uniqueness
    existing_user = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    # Validate role
    role = payload.role.lower().strip()
    if role not in ("admin", "evaluator", "viewer"):
        raise HTTPException(status_code=400, detail="Role must be one of: 'admin', 'evaluator', 'viewer'")

    initial_password = payload.password or secrets.token_urlsafe(12)
    new_user = User(
        email=payload.email,
        password_hash=hash_password(initial_password),
        name=payload.name,
        role=role,
        workspace_id=ctx.workspace.id,
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)

    # Record tamper-evident audit event
    await record_audit_event(
        db,
        workspace_id=ctx.workspace.id,
        action="MEMBER_ADDED",
        resource_type="member",
        resource_id=new_user.id,
        details={"email": new_user.email, "role": new_user.role, "invited_by": ctx.user_email},
        user_id=ctx.user_id,
        user_email=ctx.user_email,
        ip_address=ctx.client_ip,
    )
    await db.commit()

    return WorkspaceMemberResponse(
        id=new_user.id,
        email=new_user.email,
        name=new_user.name,
        role=new_user.role,
        workspace_id=new_user.workspace_id,
        created_at=new_user.created_at,
    )


@router.patch("/{user_id}", response_model=WorkspaceMemberResponse)
async def update_member_role(
    user_id: str,
    payload: WorkspaceMemberUpdate,
    ctx: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing workspace member's role (Admin only)."""
    target_user = (
        await db.execute(select(User).where(User.id == user_id, User.workspace_id == ctx.workspace.id))
    ).scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="Workspace member not found")

    new_role = payload.role.lower().strip()
    if new_role not in ("admin", "evaluator", "viewer"):
        raise HTTPException(status_code=400, detail="Role must be one of: 'admin', 'evaluator', 'viewer'")

    # Safety check: prevent demoting the only remaining Admin
    if target_user.role == "admin" and new_role != "admin":
        stmt = select(User).where(User.workspace_id == ctx.workspace.id, User.role == "admin")
        admin_count = len((await db.execute(stmt)).scalars().all())
        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot demote the only remaining Admin. Assign another Admin before demoting this user.",
            )

    old_role = target_user.role
    target_user.role = new_role
    await db.flush()

    # Record tamper-evident audit event
    await record_audit_event(
        db,
        workspace_id=ctx.workspace.id,
        action="MEMBER_ROLE_UPDATED",
        resource_type="member",
        resource_id=target_user.id,
        details={"user_email": target_user.email, "old_role": old_role, "new_role": new_role},
        user_id=ctx.user_id,
        user_email=ctx.user_email,
        ip_address=ctx.client_ip,
    )
    await db.commit()
    await db.refresh(target_user)

    return WorkspaceMemberResponse(
        id=target_user.id,
        email=target_user.email,
        name=target_user.name,
        role=target_user.role,
        workspace_id=target_user.workspace_id,
        created_at=target_user.created_at,
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace_member(
    user_id: str,
    ctx: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from the workspace (Admin only)."""
    target_user = (
        await db.execute(select(User).where(User.id == user_id, User.workspace_id == ctx.workspace.id))
    ).scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="Workspace member not found")

    # Safety check: Cannot remove oneself
    if ctx.user and target_user.id == ctx.user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself from the workspace.")

    # Safety check: Cannot remove the only remaining admin
    if target_user.role == "admin":
        stmt = select(User).where(User.workspace_id == ctx.workspace.id, User.role == "admin")
        admin_count = len((await db.execute(stmt)).scalars().all())
        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot remove the only remaining Admin of the workspace.",
            )

    removed_email = target_user.email
    removed_role = target_user.role
    await db.delete(target_user)

    # Record tamper-evident audit event
    await record_audit_event(
        db,
        workspace_id=ctx.workspace.id,
        action="MEMBER_REMOVED",
        resource_type="member",
        resource_id=user_id,
        details={"email": removed_email, "role": removed_role},
        user_id=ctx.user_id,
        user_email=ctx.user_email,
        ip_address=ctx.client_ip,
    )
    await db.commit()
