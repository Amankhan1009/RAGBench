"""SQLAlchemy models for Experiments and Experiment Items."""
import uuid
from typing import List, Optional
from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ragbench.db.base import Base, BaseMixin


class Experiment(Base, BaseMixin):
    """Evaluation experiment run linked to a dataset and model provider."""
    __tablename__ = "experiments"

    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    is_baseline: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    items: Mapped[List["ExperimentItem"]] = relationship(
        "ExperimentItem",
        back_populates="experiment",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class ExperimentItem(Base, BaseMixin):
    """Evaluation outcome for an individual dataset item inside an experiment run."""
    __tablename__ = "experiment_items"

    experiment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    dataset_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dataset_items.id", ondelete="CASCADE"),
        nullable=False
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="SUCCESS", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    experiment: Mapped["Experiment"] = relationship("Experiment", back_populates="items")
