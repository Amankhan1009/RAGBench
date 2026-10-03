"""Authentication, User registration, and BYOK API Key management endpoints."""
import secrets
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ragbench.core.jwt import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from ragbench.core.security import encrypt_api_key
from ragbench.db.session import get_db
from ragbench.models.user import User
from ragbench.models.workspace import Workspace, WorkspaceApiKey
from ragbench.schemas.auth import (
    ApiKeyMetadata,
    ApiKeyRegister,
    AuthTokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    WorkspaceCreate,
    WorkspaceResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication & Multi-Tenancy"])


async def get_current_workspace(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> Workspace:
    """Resolve active workspace via JWT Bearer token or X-API-Key header."""
    # 1. Check Bearer token (JWT)
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1].strip()
        try:
            payload = decode_access_token(token)
            workspace_id = payload.get("workspace_id")
            if workspace_id:
                ws = (await db.execute(select(Workspace).where(Workspace.id == workspace_id))).scalar_one_or_none()
                if ws:
                    return ws
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired JWT token")

    # 2. Check X-API-Key header
    effective_key = x_api_key or "default-workspace-key"
    res = await db.execute(select(Workspace).where(Workspace.api_key == effective_key))
    workspace = res.scalar_one_or_none()

    if not workspace:
        if effective_key == "default-workspace-key":
            workspace = Workspace(name="Default Workspace", api_key="default-workspace-key")
            db.add(workspace)
            await db.commit()
            await db.refresh(workspace)
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid X-API-Key header")
    return workspace


@router.post("/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user and provision their personal workspace."""
    existing_user = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    # Create private workspace
    workspace_name = f"{payload.name or payload.email.split('@')[0]}'s Workspace"
    ws_key = f"rb_ws_{secrets.token_urlsafe(24)}"
    workspace = Workspace(name=workspace_name, api_key=ws_key)
    db.add(workspace)
    await db.flush()

    # Create user with hashed password
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        workspace_id=workspace.id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await db.refresh(workspace)

    token = create_access_token({"sub": user.id, "email": user.email, "workspace_id": workspace.id})
    return AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            created_at=user.created_at,
        ),
    )


@router.post("/login", response_model=AuthTokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate with email and password to receive a JWT access token."""
    user = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    workspace = (await db.execute(select(Workspace).where(Workspace.id == user.workspace_id))).scalar_one()
    token = create_access_token({"sub": user.id, "email": user.email, "workspace_id": workspace.id})

    return AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            created_at=user.created_at,
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    workspace: Workspace = Depends(get_current_workspace),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details of the currently authenticated user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = decode_access_token(authorization.split("Bearer ", 1)[1].strip())
    user = (await db.execute(select(User).where(User.id == payload["sub"]))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        workspace_id=workspace.id,
        workspace_name=workspace.name,
        created_at=user.created_at,
    )


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

