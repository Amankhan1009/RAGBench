"""SQLAlchemy model for Production Traffic Shadowing and Golden Set Harvester."""
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import relationship

from ragbench.db.base import Base


class ShadowTrafficSample(Base):
    __tablename__ = "shadow_traffic_samples"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(100), nullable=True, index=True)

    user_query = Column(Text, nullable=False)
    model_response = Column(Text, nullable=True)
    retrieved_contexts = Column(JSON, nullable=True)

    latency_ms = Column(Float, nullable=True)
    token_count = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)

    provider = Column(String(50), nullable=True, index=True)
    model = Column(String(100), nullable=True)

    guardrails_triggered = Column(Boolean, default=False, nullable=False, index=True)
    guardrails_violations = Column(JSON, nullable=True)
    confidence_score = Column(Float, nullable=True)

    # Anomaly / edge-case flagging
    is_flagged = Column(Boolean, default=False, nullable=False, index=True)
    flag_reason = Column(String(100), nullable=True, index=True)

    # Golden Set promotion status
    is_promoted = Column(Boolean, default=False, nullable=False, index=True)
    promoted_to_dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True, index=True)

    sample_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    workspace = relationship("Workspace")
    promoted_dataset = relationship("Dataset")
