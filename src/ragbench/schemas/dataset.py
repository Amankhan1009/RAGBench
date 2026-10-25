"""Pydantic schemas for Datasets and Dataset Items."""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class DatasetItemCreate(BaseModel):
    query: str = Field(description="The evaluation prompt or user query")
    expected_output: Optional[str] = Field(default=None, description="Ground truth answer")
    contexts: List[str] = Field(default_factory=list, description="Ground truth or retrieved context chunks")
    item_metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata tags")

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "context" in data and "contexts" not in data:
                ctx = data["context"]
                data["contexts"] = ctx if isinstance(ctx, list) else [str(ctx)]
            if "metadata" in data and "item_metadata" not in data:
                data["item_metadata"] = data["metadata"]
        return data


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
    workspace_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: List[DatasetItemResponse] = []

    model_config = {"from_attributes": True}


class SyntheticDatasetRequest(BaseModel):
    raw_text: str = Field(
        min_length=50,
        max_length=50000,
        description="Raw source text, documentation, or FAQ",
    )
    num_samples: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of synthetic samples to generate",
    )
    difficulty: str = Field(
        default="mixed",
        description="Difficulty distribution: factual, reasoning, adversarial, or mixed",
    )
    provider_name: str = Field(
        default="groq",
        description="LLM provider to use for synthesis",
    )
    model_name: Optional[str] = Field(default=None, description="Model identifier")
    api_key: Optional[str] = Field(default=None, description="Optional BYOK API key override")


class SyntheticItemPreview(BaseModel):
    query: str
    expected_output: str
    contexts: List[str] = Field(default_factory=list)
    difficulty: str = "factual"
    source_snippet: Optional[str] = None


class SyntheticDatasetResponse(BaseModel):
    items: List[SyntheticItemPreview]
    total_generated: int
    provider_used: str
    model_used: str
    latency_ms: float


class DatasetIngestRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255, description="Dataset name")
    description: Optional[str] = Field(default=None, description="Dataset description")
    version: str = Field(default="1.0.0", description="Dataset version")
    file_format: str = Field(default="csv", description="File format: csv, jsonl, or json")
    content: str = Field(min_length=1, description="Raw file contents")
    column_mapping: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional mapping from schema fields (query, expected_output, contexts) to custom column names",
    )


class DatasetIngestResponse(BaseModel):
    dataset: DatasetResponse
    total_ingested: int
    skipped_rows: int
    warnings: List[str] = []
