from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usage_log import UsageLog
from app.schemas.extraction import LlmUsage


class UsageLogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record(self, project_id: str, call_type: str, usage: LlmUsage) -> UsageLog:
        row = UsageLog(
            project_id=project_id,
            call_type=call_type,
            model=usage.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def list_since(self, project_id: str, since: datetime | None) -> list[UsageLog]:
        stmt = select(UsageLog).where(UsageLog.project_id == project_id)
        if since is not None:
            stmt = stmt.where(UsageLog.created_at > since)
        return list(self.db.execute(stmt).scalars())
