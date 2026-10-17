import uuid

from pydantic import BaseModel, Field

from app.models.enums import UsageOutcome


class OutcomeReport(BaseModel):
    retrieval_id: uuid.UUID
    outcome: UsageOutcome
    used_memory_ids: list[uuid.UUID] = Field(default_factory=list)
    reward: float | None = None


class MemoryConfirmation(BaseModel):
    note: str | None = None


class MemoryCorrection(BaseModel):
    note: str | None = None


class OutcomeResponse(BaseModel):
    retrieval_id: uuid.UUID
    updated_memories: int
