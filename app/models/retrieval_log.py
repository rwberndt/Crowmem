import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RetrievalLog(Base):
    """Durable record of what a /recall call returned and why.

    Not named in the guide, but required to make /outcomes meaningful (it
    needs to know what was actually offered) and to satisfy "every ranking
    decision must be explainable" (guide invariant 10) with an audit trail.

    project_id (added in migration 0003): duplicates goal_state["project"]
    as a plain indexed column so project-scoped wipes/queries don't need a
    JSONB predicate.
    """

    __tablename__ = "retrieval_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    query_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    goal_state: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    returned_memory_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    scores_and_reasons: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
