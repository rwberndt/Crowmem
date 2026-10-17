import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.belief import Belief
from app.models.enums import BeliefStatus


class BeliefRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, belief: Belief) -> Belief:
        self.db.add(belief)
        self.db.flush()
        return belief

    def get(self, belief_id: uuid.UUID) -> Belief | None:
        return self.db.get(Belief, belief_id)

    def find_active(self, subject: str, predicate: str) -> Belief | None:
        stmt = select(Belief).where(
            Belief.subject == subject, Belief.predicate == predicate, Belief.status == BeliefStatus.active
        )
        return self.db.execute(stmt).scalars().first()

    def list(self, subject: str | None = None, predicate: str | None = None, status: BeliefStatus | None = None) -> list[Belief]:
        stmt = select(Belief)
        if subject is not None:
            stmt = stmt.where(Belief.subject == subject)
        if predicate is not None:
            stmt = stmt.where(Belief.predicate == predicate)
        if status is not None:
            stmt = stmt.where(Belief.status == status)
        stmt = stmt.order_by(Belief.observed_at.desc())
        return list(self.db.execute(stmt).scalars())
