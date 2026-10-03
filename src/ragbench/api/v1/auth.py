"""Authentication and BYOK API Key management endpoints."""
import secrets
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ragbench.core.security import encrypt_api_key
from ragbench.db.session import get_db
from ragbench.models.workspace import Workspace, WorkspaceApiKey
from ragbench.schemas.auth import ApiKeyMetadata, ApiKeyRegister, WorkspaceCreate, WorkspaceResponse

router = APIRouter(prefix="/auth", tags=["Authentication & Multi-Tenancy"])


async def get_current_workspace(
    x_api_key: str = Header(default="default-workspace-key", alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> Workspace:
    """Resolve active workspace via X-API-Key header or auto-provision default workspace."""
    stmt = select(Workspace).where(Workspace.api_key == x_api_key)
    res = await db.execute(stmt)
    workspace = res.scalar_one_or_none()

    if not workspace:
        if x_api_key == "default-workspace-key":
            workspace = Workspace(
                name="Default Workspace",
                api_key="default-workspace-key",
            )
            db.add(workspace)
            await db.commit()
            await db.refresh(workspace)
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing X-API-Key header",
            )
    return workspace


@router.post("/workspaces", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new multi-tenant workspace and generate its secret API key."""
    existing = await db.execute(select(Workspace).where(Workspace.name == payload.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Workspace name already exists")

    generated_key = f"rb_ws_{secrets.token_urlsafe(24)}"
    workspace = Workspace(name=payload.name, api_key=generated_key)
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.post("/keys", response_model=ApiKeyMetadata, status_code=status.HTTP_201_CREATED)
async def register_byok_key(
    payload: ApiKeyRegister,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Register and Fernet-encrypt a BYOK cloud provider API key for the active workspace."""
    encrypted = encrypt_api_key(payload.api_key)

    stmt = select(WorkspaceApiKey).where(
        WorkspaceApiKey.workspace_id == workspace.id,
        WorkspaceApiKey.provider == payload.provider.lower(),
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()

    if existing:
        existing.encrypted_key = encrypted
        key_record = existing
    else:
        key_record = WorkspaceApiKey(
            workspace_id=workspace.id,
            provider=payload.provider.lower(),
            encrypted_key=encrypted,
        )
        db.add(key_record)

    await db.commit()
    await db.refresh(key_record)

    preview = f"{payload.api_key[:6]}...{payload.api_key[-4:]}" if len(payload.api_key) > 10 else "***"
    return ApiKeyMetadata(
        id=key_record.id,
        provider=key_record.provider,
        key_preview=preview,
        created_at=key_record.created_at,
    )


@router.get("/keys", response_model=List[ApiKeyMetadata])
async def list_byok_keys(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """List all registered BYOK keys in the current workspace (metadata only, zero secret leakage)."""
    stmt = select(WorkspaceApiKey).where(WorkspaceApiKey.workspace_id == workspace.id)
    records = (await db.execute(stmt)).scalars().all()

    return [
        ApiKeyMetadata(
            id=r.id,
            provider=r.provider,
            key_preview="••••••••••••",
            created_at=r.created_at,
        )
        for r in records
    ]
