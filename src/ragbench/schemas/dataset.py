"""Pydantic schemas for Datasets and Dataset Items."""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DatasetItemCreate(BaseModel):
    query: str = Field(description="The evaluation prompt or user query")
    expected_output: Optional[str] = Field(default=None, description="Ground truth answer")
    contexts: List[str] = Field(default_factory=list, description="Ground truth or retrieved context chunks")
    item_metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata tags")


class DatasetItemResponse(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    query: str
    expected_output: Optional[str] = None
    contexts: List[str] = []
    item_metadata: Dict[str, Any] = {}
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255, description="Dataset name")
    description: Optional[str] = Field(default=None, description="Dataset summary")
    version: str = Field(default="1.0.0", description="SemVer dataset version")
    items: List[DatasetItemCreate] = Field(default_factory=list, description="Initial dataset items")


class DatasetResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    version: str
    created_at: datetime
    updated_at: datetime
    items: List[DatasetItemResponse] = []

    model_config = {"from_attributes": True}
