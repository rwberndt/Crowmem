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


class RetrievalLogResponse(BaseModel):
    """What a recall actually returned and why -- the Mem Off adapter's
    receipt.sh reformats this into the contract's ids/ranks/reasons shape."""

    retrieval_id: uuid.UUID
    project_id: str
    query_text: str | None
    returned_memory_ids: list[str]
    scores_and_reasons: dict

    model_config = {"from_attributes": True}

    @classmethod
    def from_log(cls, log) -> "RetrievalLogResponse":
        return cls(
            retrieval_id=log.id,
            project_id=log.project_id,
            query_text=log.query_text,
            returned_memory_ids=log.returned_memory_ids,
            scores_and_reasons=log.scores_and_reasons,
        )
