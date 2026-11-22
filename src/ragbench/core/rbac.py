"""Enterprise Role-Based Access Control (RBAC) definitions and dependencies."""
from enum import Enum
from typing import List, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ragbench.core.jwt import decode_access_token
from ragbench.db.session import get_db
from ragbench.models.user import User
from ragbench.models.workspace import Workspace


class UserRole(str, Enum):
    ADMIN = "admin"
    EVALUATOR = "evaluator"
    VIEWER = "viewer"


class AuthContext:
    """Encapsulates authenticated caller identity, tenant workspace, role, and client metadata."""

    def __init__(
        self,
        workspace: Workspace,
        user: Optional[User] = None,
        role: str = "admin",
        client_ip: Optional[str] = None,
    ):
        self.workspace = workspace
        self.user = user
        self.role = role.lower() if role else "admin"
        self.client_ip = client_ip

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN.value

    @property
    def is_evaluator(self) -> bool:
        return self.role in (UserRole.ADMIN.value, UserRole.EVALUATOR.value)

    @property
    def is_viewer(self) -> bool:
        return self.role in (UserRole.ADMIN.value, UserRole.EVALUATOR.value, UserRole.VIEWER.value)

    @property
    def user_id(self) -> Optional[str]:
        return self.user.id if self.user else None

    @property
    def user_email(self) -> Optional[str]:
        return self.user.email if self.user else "service-account@workspace"


async def get_auth_context(
    request: Request,
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    """Resolve active tenant AuthContext from Bearer JWT or secret X-API-Key header."""
    # Resolve client IP address
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    elif request.client:
        client_ip = request.client.host
    else:
        client_ip = "127.0.0.1"

    # 1. Bearer JWT Token resolution
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1].strip()
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub")
            ws_id = payload.get("workspace_id")

            user: Optional[User] = None
            if user_id:
                user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()

            effective_ws_id = (user.workspace_id if user else None) or ws_id
            if effective_ws_id:
                workspace = (await db.execute(select(Workspace).where(Workspace.id == effective_ws_id))).scalar_one_or_none()
                if workspace:
                    role = (user.role if user and user.role else payload.get("role", "admin")).lower()
                    return AuthContext(workspace=workspace, user=user, role=role, client_ip=client_ip)
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired JWT token")

    # 2. X-API-Key header resolution
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

    # Service / CLI API keys inherit full Admin privileges
    return AuthContext(workspace=workspace, user=None, role="admin", client_ip=client_ip)


def require_roles(allowed_roles: List[str]):
    """FastAPI dependency factory enforcing that caller role is within the permitted set."""
    normalized_allowed = [r.lower() for r in allowed_roles]

    async def role_dependency(ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if ctx.role not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Operation forbidden: requires one of {allowed_roles} roles. "
                    f"Current user role is '{ctx.role}'."
                ),
            )
        return ctx

    return role_dependency


require_admin = require_roles(["admin"])
require_evaluator = require_roles(["admin", "evaluator"])
require_viewer = require_roles(["admin", "evaluator", "viewer"])
