"""Pydantic schemas for multi-tenant workspace authentication, users, and BYOK key registration."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(description="Unique workspace name", min_length=2, max_length=100)


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    api_key: str = Field(description="Secret workspace API token (shown once upon creation)")
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ApiKeyRegister(BaseModel):
    provider: str = Field(description="LLM Provider: groq, openai, anthropic, or google")
    api_key: str = Field(description="Plaintext BYOK API key (encrypted before storage)", min_length=8)


class ApiKeyMetadata(BaseModel):
    id: str
    provider: str
    key_preview: str = Field(description="Masked key preview (never exposes full key)")
    created_at: Optional[datetime] = None


class UserRegister(BaseModel):
    email: str = Field(..., description="User email address", min_length=5, max_length=255)
    password: str = Field(description="Plaintext user password", min_length=6)
    name: Optional[str] = Field(default=None, description="Optional user display name")


class UserLogin(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(description="Plaintext user password")


class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    role: str = "admin"
    workspace_id: str
    workspace_name: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class WorkspaceMemberInvite(BaseModel):
    email: str = Field(..., description="Email of the new member to invite", min_length=5, max_length=255)
    name: Optional[str] = Field(default=None, description="Optional display name")
    role: str = Field(default="evaluator", description="Role: admin, evaluator, or viewer")
    password: Optional[str] = Field(default=None, description="Optional initial password (defaults to secure random)")


class WorkspaceMemberUpdate(BaseModel):
    role: str = Field(..., description="Updated role: admin, evaluator, or viewer")


class WorkspaceMemberResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    role: str
    workspace_id: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

