import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import UsageOutcome


class MemoryUsage(Base):
    """Tracks whether a memory returned by a specific retrieval helped."""

    __tablename__ = "memory_usage"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    retrieval_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("retrieval_log.id", ondelete="CASCADE"), nullable=False, index=True
    )
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    outcome: Mapped[UsageOutcome | None] = mapped_column(SAEnum(UsageOutcome, name="usage_outcome"), nullable=True)
    reward: Mapped[float | None] = mapped_column(Float, nullable=True)
