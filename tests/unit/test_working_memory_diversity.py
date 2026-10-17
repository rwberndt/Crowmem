import uuid
from datetime import datetime, timezone

from app.models.enums import MemoryType
from app.models.memory import Memory
from app.services.activation_service import ActivationBreakdown
from app.services.working_memory_service import estimate_tokens, select_working_memory


def make_memory(content="memory content", embedding=None) -> Memory:
    return Memory(
        id=uuid.uuid4(), content=content, memory_type=MemoryType.fact, project_id="p",
        created_at=datetime.now(timezone.utc), strength=0.5, utility_score=0.5, risk_score=0.0, confidence=0.5,
        retrieval_count=0, successful_use_count=0, failed_use_count=0, decay_rate=0.02, protected=False,
        embedding=embedding, last_accessed_at=None,
    )


def candidate(activation: float, embedding=None, content="memory content"):
    memory = make_memory(embedding=embedding, content=content)
    return memory, ActivationBreakdown(memory_id=memory.id, activation=activation, components={}, reasons=[])


def test_never_exceeds_max_slots():
    candidates = [candidate(0.9 - i * 0.01) for i in range(50)]
    selected = select_working_memory(candidates, max_slots=4, max_tokens=10_000, diversity_penalty_weight=0.3)
    assert len(selected) <= 4


def test_diversity_filter_prevents_four_near_identical_memories():
    """Guide section 29 'Context Pollution' failure mode: four returned
    memories should not all be variants of the same fact."""
    duplicate_embedding = [1.0, 0.0, 0.0]
    distinct_embedding = [0.0, 1.0, 0.0]

    duplicates = [candidate(0.9, embedding=duplicate_embedding, content=f"dup-{i}") for i in range(4)]
    distinct = candidate(0.85, embedding=distinct_embedding, content="distinct")

    selected = select_working_memory([*duplicates, distinct], max_slots=4, max_tokens=10_000, diversity_penalty_weight=0.5)

    selected_contents = {slot.memory.content for slot in selected}
    assert "distinct" in selected_contents
    assert not all(c.startswith("dup-") for c in selected_contents)


def test_token_budget_is_respected():
    long_content = "x" * 4000  # ~1000 tokens
    candidates = [candidate(0.9, content=long_content) for _ in range(5)]
    selected = select_working_memory(candidates, max_slots=4, max_tokens=1500, diversity_penalty_weight=0.3)
    total_tokens = sum(estimate_tokens(slot.memory.content) for slot in selected)
    assert total_tokens <= 1500
    assert len(selected) <= 2


def test_zero_activation_candidates_are_not_selected():
    candidates = [candidate(0.0) for _ in range(3)]
    selected = select_working_memory(candidates, max_slots=4, max_tokens=10_000, diversity_penalty_weight=0.3)
    assert selected == []


def test_empty_candidates_returns_empty():
    assert select_working_memory([], max_slots=4, max_tokens=800, diversity_penalty_weight=0.3) == []
