import uuid

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models.enums import MemoryType
from app.models.memory import Memory


class MemoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, memory: Memory) -> Memory:
        self.db.add(memory)
        self.db.flush()
        return memory

    def get(self, memory_id: uuid.UUID) -> Memory | None:
        return self.db.get(Memory, memory_id)

    def has_any(self, project_id: str) -> bool:
        return bool(self.db.scalar(select(exists().where(Memory.project_id == project_id))))

    def find_most_similar(
        self, project_id: str, memory_type: MemoryType, embedding: list[float], limit: int = 1
    ) -> list[tuple[Memory, float]]:
        """Returns (memory, cosine_distance) pairs ordered by distance ascending
        (0 = identical). Used for deduplication (guide section 10)."""
        distance_col = Memory.embedding.cosine_distance(embedding).label("distance")
        stmt = (
            select(Memory, distance_col)
            .where(Memory.project_id == project_id, Memory.memory_type == memory_type, Memory.embedding.is_not(None))
            .order_by(distance_col)
            .limit(limit)
        )
        return [(row[0], row[1]) for row in self.db.execute(stmt).all()]

    def list_by_project(self, project_id: str, limit: int = 100) -> list[Memory]:
        stmt = select(Memory).where(Memory.project_id == project_id).order_by(Memory.created_at.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars())

    def semantic_candidates(self, project_id: str, embedding: list[float], limit: int = 10) -> list[tuple[Memory, float]]:
        distance_col = Memory.embedding.cosine_distance(embedding).label("distance")
        stmt = (
            select(Memory, distance_col)
            .where(Memory.project_id == project_id, Memory.embedding.is_not(None))
            .order_by(distance_col)
            .limit(limit)
        )
        return [(row[0], row[1]) for row in self.db.execute(stmt).all()]

    def list_protected(self, project_id: str) -> list[Memory]:
        stmt = select(Memory).where(Memory.project_id == project_id, Memory.protected.is_(True))
        return list(self.db.execute(stmt).scalars())

    def list_all(self) -> list[Memory]:
        return list(self.db.execute(select(Memory)).scalars())
