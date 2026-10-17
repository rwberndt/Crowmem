import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.models.association import Association
from app.models.memory import Memory
from app.services.association_service import compute_context_match, matched_association_reasons
from app.services.novelty_service import cosine_similarity


@dataclass
class ActivationBreakdown:
    memory_id: uuid.UUID
    activation: float
    components: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)


def _recency_score(last_accessed_at: datetime | None, created_at: datetime, half_life_days: float, now: datetime) -> float:
    reference = last_accessed_at or created_at
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    days = max(0.0, (now - reference).total_seconds() / 86400.0)
    decay_const = math.log(2) / half_life_days if half_life_days > 0 else 0.0
    return math.exp(-decay_const * days)


def compute_activation(
    memory: Memory,
    query_embedding: list[float],
    goal_pairs: set[tuple[str, str]],
    associations: list[Association],
    weights: dict[str, float],
    recency_half_life_days: float,
    now: datetime | None = None,
) -> ActivationBreakdown:
    """Additive activation formula (guide section 14). Similarity alone never
    determines ranking (invariant 9) -- it's one of eight terms."""
    now = now or datetime.now(timezone.utc)

    semantic_relevance = 0.0
    if memory.embedding is not None and query_embedding:
        semantic_relevance = max(0.0, cosine_similarity(query_embedding, memory.embedding))

    context_match = compute_context_match(goal_pairs, associations)
    expected_utility = memory.utility_score
    strength = memory.strength
    confidence = memory.confidence
    risk_relevance = memory.risk_score
    recency = _recency_score(memory.last_accessed_at, memory.created_at, recency_half_life_days, now)
    total_uses = memory.successful_use_count + memory.failed_use_count
    historical_success = (memory.successful_use_count + 0.5) / (total_uses + 1.0)

    components = {
        "semantic_relevance": weights.get("semantic_relevance", 0.0) * semantic_relevance,
        "context_match": weights.get("context_match", 0.0) * context_match,
        "expected_utility": weights.get("expected_utility", 0.0) * expected_utility,
        "strength": weights.get("strength", 0.0) * strength,
        "confidence": weights.get("confidence", 0.0) * confidence,
        "risk_relevance": weights.get("risk_relevance", 0.0) * risk_relevance,
        "recency": weights.get("recency", 0.0) * recency,
        "historical_success": weights.get("historical_success", 0.0) * historical_success,
    }
    activation = sum(components.values())

    reasons = matched_association_reasons(goal_pairs, associations)
    if risk_relevance >= 0.7:
        reasons.append("high_risk")
    if semantic_relevance >= 0.5:
        reasons.append("semantic_match")
    if memory.successful_use_count > 0:
        reasons.append("successful_previous_use")
    if memory.protected:
        reasons.append("protected_memory")
    if not reasons:
        reasons.append("baseline_candidate")

    return ActivationBreakdown(memory_id=memory.id, activation=activation, components=components, reasons=reasons)
