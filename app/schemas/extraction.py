from pydantic import BaseModel, Field

from app.models.enums import BeliefRelation


class MemoryCandidate(BaseModel):
    content: str
    memory_type: str
    risk_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    associations: dict[str, str] = Field(default_factory=dict)


class MemoryExtractionResult(BaseModel):
    memories: list[MemoryCandidate] = Field(default_factory=list)


class BeliefRelationClassification(BaseModel):
    relation: BeliefRelation
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = ""


class BeliefCandidate(BaseModel):
    subject: str
    predicate: str
    object: str
    confidence: float = Field(ge=0.0, le=1.0)


class BeliefExtractionResult(BaseModel):
    beliefs: list[BeliefCandidate] = Field(default_factory=list)
