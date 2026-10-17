import uuid

from sqlalchemy.orm import Session

from app.models.memory_usage import MemoryUsage
from app.models.retrieval_log import RetrievalLog


class RetrievalRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_log(self, log: RetrievalLog) -> RetrievalLog:
        self.db.add(log)
        self.db.flush()
        return log

    def get_log(self, retrieval_id: uuid.UUID) -> RetrievalLog | None:
        return self.db.get(RetrievalLog, retrieval_id)

    def create_usage(self, usage: MemoryUsage) -> MemoryUsage:
        self.db.add(usage)
        self.db.flush()
        return usage

    def list_usage_for_retrieval(self, retrieval_id: uuid.UUID) -> list[MemoryUsage]:
        from sqlalchemy import select

        stmt = select(MemoryUsage).where(MemoryUsage.retrieval_id == retrieval_id)
        return list(self.db.execute(stmt).scalars())

    def list_recent_for_project(self, project_id: str, limit: int = 5) -> list[RetrievalLog]:
        from sqlalchemy import select

        stmt = (
            select(RetrievalLog)
            .where(RetrievalLog.project_id == project_id)
            .order_by(RetrievalLog.created_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars())
