"""Pydantic schemas for multi-tenant workspace authentication and BYOK key registration."""
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