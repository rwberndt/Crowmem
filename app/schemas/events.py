import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    content: str
    event_type: str
    project_id: str
    agent_id: str | None = None
    source: str | None = None
    metadata: dict = Field(default_factory=dict)


class EventResponse(BaseModel):
    id: uuid.UUID
    content: str
    event_type: str
    project_id: str
    observed_at: datetime
    salience_score: float | None
    encoded: bool

    model_config = {"from_attributes": True}
