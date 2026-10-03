"""Dataset and version management REST API endpoints."""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ragbench.db.session import get_db
from ragbench.models.dataset import Dataset, DatasetItem
from ragbench.schemas.dataset import (
    DatasetCreate,
    DatasetItemCreate,
    DatasetItemResponse,
    DatasetResponse,
)

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.post("", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(payload: DatasetCreate, db: AsyncSession = Depends(get_db)):
    """Create a new evaluation dataset and optional initial items."""
    dataset = Dataset(
        name=payload.name,
        description=payload.description,
        version=payload.version
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
async def list_datasets(db: AsyncSession = Depends(get_db)):
    """List all registered evaluation datasets."""
    stmt = select(Dataset).order_by(Dataset.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Retrieve a specific dataset by ID with its evaluation items."""
    stmt = select(Dataset).where(Dataset.id == dataset_id)
    result = await db.execute(stmt)
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found"
        )
    return dataset


@router.post("/{dataset_id}/items", response_model=List[DatasetItemResponse], status_code=status.HTTP_201_CREATED)
async def bulk_add_items(
    dataset_id: uuid.UUID,
    items_data: List[DatasetItemCreate],
    db: AsyncSession = Depends(get_db)
):
    """Bulk import evaluation items into an existing dataset."""
    stmt = select(Dataset).where(Dataset.id == dataset_id)
    result = await db.execute(stmt)
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found"
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
