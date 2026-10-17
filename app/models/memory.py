import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.models.base import Base
from app.models.enums import MemoryType

try:
    from sqlalchemy.dialects.postgresql import UUID
except ImportError:  # pragma: no cover
    from sqlalchemy import String as UUID  # type: ignore

_EMBEDDING_DIM = get_settings().embedding_dim


class Memory(Base):
    """A durable memory derived from one or more episodes.

    Reinforcement (M6) only ever writes strength/utility_score/retrieval_count/
    successful_use_count/failed_use_count. Confidence changes only via explicit
    confirm/correct — never via reinforcement (guide invariants 2/3).
    """

    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    memory_type: Mapped[MemoryType] = mapped_column(SAEnum(MemoryType, name="memory_type"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_decayed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    strength: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    utility_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)

    retrieval_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    successful_use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    decay_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.02)
    protected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    embedding: Mapped[list[float] | None] = mapped_column(Vector(_EMBEDDING_DIM), nullable=True)
