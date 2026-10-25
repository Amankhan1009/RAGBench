"""Dataset and version management REST API endpoints with multi-tenant workspace isolation."""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ragbench.api.v1.auth import get_current_workspace
from ragbench.db.session import get_db
from ragbench.models.dataset import Dataset, DatasetItem
from ragbench.models.workspace import Workspace
from ragbench.schemas.dataset import (
    DatasetCreate,
    DatasetItemCreate,
    DatasetItemResponse,
    DatasetResponse,
)

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.post("", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    payload: DatasetCreate,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Create a new evaluation dataset for the current workspace and optional initial items."""
    dataset = Dataset(
        name=payload.name,
        description=payload.description,
        version=payload.version,
        workspace_id=workspace.id,
    )
    db.add(dataset)
    await db.flush()

    for item_data in payload.items:
        item = DatasetItem(
            dataset_id=dataset.id,
            query=item_data.query,
            expected_output=item_data.expected_output,
            contexts=item_data.contexts,
            item_metadata=item_data.item_metadata
        )
        db.add(item)

    await db.commit()
    await db.refresh(dataset)
    return dataset


@router.get("", response_model=List[DatasetResponse])
async def list_datasets(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """List all registered evaluation datasets belonging to the active workspace."""
    stmt = (
        select(Dataset)
        .where(Dataset.workspace_id == workspace.id)
        .order_by(Dataset.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a specific dataset by ID with its evaluation items within the active workspace."""
    stmt = select(Dataset).where(
        Dataset.id == dataset_id,
        Dataset.workspace_id == workspace.id,
    )
    result = await db.execute(stmt)
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found in current workspace"
        )
    return dataset


@router.post("/{dataset_id}/items", response_model=List[DatasetItemResponse], status_code=status.HTTP_201_CREATED)
async def bulk_add_items(
    dataset_id: uuid.UUID,
    items_data: List[DatasetItemCreate],
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Bulk import evaluation items into an existing dataset in the active workspace."""
    stmt = select(Dataset).where(
        Dataset.id == dataset_id,
        Dataset.workspace_id == workspace.id,
    )
    result = await db.execute(stmt)
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found in current workspace"
        )

    new_items = []
    for item_data in items_data:
        item = DatasetItem(
            dataset_id=dataset.id,
            query=item_data.query,
            expected_output=item_data.expected_output,
            contexts=item_data.contexts,
            item_metadata=item_data.item_metadata
        )
        db.add(item)
        new_items.append(item)

    await db.commit()
    for item in new_items:
        await db.refresh(item)
    return new_items


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    dataset_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Delete a dataset and all associated items belonging to the active workspace."""
    stmt = select(Dataset).where(
        Dataset.id == dataset_id,
        Dataset.workspace_id == workspace.id,
    )
    result = await db.execute(stmt)
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found in current workspace"
        )

    await db.delete(dataset)
    await db.commit()
    return None
