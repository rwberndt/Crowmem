import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import BeliefStatus


class BeliefResponse(BaseModel):
    id: uuid.UUID
    project_id: str
    subject: str
    predicate: str
    object: str
    status: BeliefStatus
    confidence: float
    valid_from: datetime | None
    valid_to: datetime | None
    observed_at: datetime

    model_config = {"from_attributes": True}
