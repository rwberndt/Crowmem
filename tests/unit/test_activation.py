import uuid
from datetime import datetime, timezone

from app.models.association import Association
from app.models.enums import MemoryType
from app.models.memory import Memory
from app.services.activation_service import compute_activation

ZERO_WEIGHTS = {
    "semantic_relevance": 0.0, "context_match": 0.0, "expected_utility": 0.0, "strength": 0.0,
    "confidence": 0.0, "risk_relevance": 0.0, "recency": 0.0, "historical_success": 0.0,
}


def make_memory(**overrides) -> Memory:
    defaults = dict(
        id=uuid.uuid4(), content="test memory", memory_type=MemoryType.warning, project_id="peach",
        created_at=datetime.now(timezone.utc), strength=0.5, utility_score=0.5, risk_score=0.5, confidence=0.5,
        retrieval_count=0, successful_use_count=0, failed_use_count=0, decay_rate=0.02, protected=False,
        embedding=None, last_accessed_at=None,
    )
    defaults.update(overrides)
    return Memory(**defaults)


def test_similarity_alone_does_not_determine_ranking():
    """Invariant 9: a high-similarity, zero-context memory should not
    automatically outrank a lower-similarity, high-context one once all
    eight terms are weighted."""
    weights = {**ZERO_WEIGHTS, "semantic_relevance": 0.3, "context_match": 0.7}

    high_sim_no_context = make_memory(embedding=[1.0, 0.0, 0.0])
    low_sim_high_context = make_memory(embedding=[0.0, 1.0, 0.0])

    goal_pairs = {("environment", "production")}
    matching_association = [Association(memory_id=low_sim_high_context.id, key="environment", value="production", weight=1.0)]

    breakdown_high_sim = compute_activation(high_sim_no_context, [1.0, 0.0, 0.0], goal_pairs, [], weights, 14)
    breakdown_low_sim = compute_activation(low_sim_high_context, [1.0, 0.0, 0.0], goal_pairs, matching_association, weights, 14)

    assert breakdown_low_sim.activation > breakdown_high_sim.activation
    assert "environment_match" in breakdown_low_sim.reasons


def test_activation_is_additive_sum_of_weighted_terms():
    weights = {**ZERO_WEIGHTS, "expected_utility": 1.0}
    memory = make_memory(utility_score=0.7)
    breakdown = compute_activation(memory, [], set(), [], weights, 14)
    assert breakdown.activation == 0.7
    assert breakdown.components["expected_utility"] == 0.7


def test_high_risk_reason_present_above_threshold():
    weights = {**ZERO_WEIGHTS, "risk_relevance": 1.0}
    memory = make_memory(risk_score=0.9)
    breakdown = compute_activation(memory, [], set(), [], weights, 14)
    assert "high_risk" in breakdown.reasons


def test_protected_memory_reason_present():
    memory = make_memory(protected=True)
    breakdown = compute_activation(memory, [], set(), [], ZERO_WEIGHTS, 14)
    assert "protected_memory" in breakdown.reasons
