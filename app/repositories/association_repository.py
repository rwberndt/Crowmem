import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.association import Association
from app.models.memory import Memory


class AssociationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, association: Association) -> Association:
        self.db.add(association)
        self.db.flush()
        return association

    def list_for_memory(self, memory_id: uuid.UUID) -> list[Association]:
        stmt = select(Association).where(Association.memory_id == memory_id)
        return list(self.db.execute(stmt).scalars())

    def list_for_memories(self, memory_ids: list[uuid.UUID]) -> list[Association]:
        if not memory_ids:
            return []
        stmt = select(Association).where(Association.memory_id.in_(memory_ids))
        return list(self.db.execute(stmt).scalars())

    def find_memory_ids_matching(self, project_id: str, goal_pairs: set[tuple[str, str]]) -> set[uuid.UUID]:
        """Scoped to `project_id` -- without this join/filter, two memories
        in different projects that happen to share a generic association
        value (e.g. environment=production) would leak across projects."""
        if not goal_pairs:
            return set()
        conditions = [(Association.key == key) & (Association.value == value) for key, value in goal_pairs]
        combined = conditions[0]
        for cond in conditions[1:]:
            combined = combined | cond
        stmt = (
            select(Association.memory_id)
            .join(Memory, Memory.id == Association.memory_id)
            .where(Memory.project_id == project_id, combined)
            .distinct()
        )
        return set(self.db.execute(stmt).scalars())
