import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import BeliefRelation, BeliefStatus


class Belief(Base):
    """A structured fact representing current or historical knowledge.

    Every belief must remain traceable to one or more episodes via Evidence
    (guide invariant 4) — belief_resolver writes Belief + Evidence atomically.

    project_id (added in migration 0003): the guide's own schema has no
    project scoping on beliefs, but without it two projects sharing a
    generic subject could leak into each other on recall/wipe -- the same
    class of bug found and fixed on the association-matching recall channel.
    """

    __tablename__ = "beliefs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    predicate: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    object: Mapped[str] = mapped_column(String(500), nullable=False)

    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    status: Mapped[BeliefStatus] = mapped_column(
        SAEnum(BeliefStatus, name="belief_status"), nullable=False, default=BeliefStatus.active
    )

    # SET NULL, not CASCADE: deleting the newer belief in a project wipe
    # shouldn't cascade into deleting the older one it superseded.
    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("beliefs.id", ondelete="SET NULL"), nullable=True
    )
    relation: Mapped[BeliefRelation | None] = mapped_column(
        SAEnum(BeliefRelation, name="belief_relation"), nullable=True
    )
