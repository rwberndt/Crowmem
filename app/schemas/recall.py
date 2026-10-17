import uuid

from pydantic import BaseModel, Field

from app.schemas.goals import GoalState


class RecallRequest(BaseModel):
    query: str
    goal_state: GoalState = Field(default_factory=GoalState)
    max_memories: int | None = None
    max_tokens: int | None = None


class WorkingMemoryItem(BaseModel):
    id: uuid.UUID
    content: str
    activation: float
    reason: list[str]


class RecallResponse(BaseModel):
    retrieval_id: uuid.UUID
    working_memory: list[WorkingMemoryItem]
