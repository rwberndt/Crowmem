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


class LlmUsage(BaseModel):
    """Real token counts for one Anthropic call this engine made on its own
    behalf. Captured whenever the API call itself succeeded, even if the
    structured output afterward failed validation -- tokens were spent
    either way, and cost accounting (e.g. Mem Off's usage.sh) must never
    silently treat a validation failure as zero-cost.
    """

    model: str
    input_tokens: int = 0
    output_tokens: int = 0
