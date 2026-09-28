"""SQLAlchemy models for Datasets and Dataset Items."""
import uuid
from typing import List, Optional
from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ragbench.db.base import Base, BaseMixin


class Dataset(Base, BaseMixin):
    """Evaluation dataset container and version tracker."""
    __tablename__ = "datasets"

    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)

    items: Mapped[List["DatasetItem"]] = relationship(
        "DatasetItem",
        back_populates="dataset",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class DatasetItem(Base, BaseMixin):
    """Individual evaluation sample row containing query, expected answer, and retrieved contexts."""
    __tablename__ = "dataset_items"

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contexts: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    item_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="items")
