import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import MemoryType


class MemoryResponse(BaseModel):
    id: uuid.UUID
    content: str
    memory_type: MemoryType
    project_id: str
    created_at: datetime
    strength: float
    utility_score: float
    risk_score: float
    confidence: float
    retrieval_count: int
    successful_use_count: int
    failed_use_count: int
    protected: bool

    model_config = {"from_attributes": True}
