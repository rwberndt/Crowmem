import uuid
from datetime import datetime

from pydantic import BaseModel


class EpisodeResponse(BaseModel):
    id: uuid.UUID
    content: str
    event_type: str
    project_id: str
    observed_at: datetime
    salience_score: float | None
    encoded: bool

    model_config = {"from_attributes": True}
