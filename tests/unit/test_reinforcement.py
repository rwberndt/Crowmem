import uuid
from datetime import datetime, timezone

from app.models.enums import MemoryType, UsageOutcome
from app.models.memory import Memory
from app.services.reinforcement_service import apply_confirmation, apply_correction, apply_outcome

DELTAS = {
    "success_used_utility": 0.10, "success_used_strength": 0.05, "unused_utility": -0.01,
    "failure_used_utility": -0.05, "confirm_confidence": 0.10, "correct_confidence": -0.25,
}


def make_memory(**overrides) -> Memory:
    defaults = dict(
        id=uuid.uuid4(), content="x", memory_type=MemoryType.fact, project_id="p",
        created_at=datetime.now(timezone.utc), strength=0.5, utility_score=0.5, risk_score=0.0, confidence=0.5,
        retrieval_count=0, successful_use_count=0, failed_use_count=0, decay_rate=0.02, protected=False,
    )
    defaults.update(overrides)
    return Memory(**defaults)


def test_successful_use_raises_utility_and_strength_not_confidence():
    memory = make_memory()
    apply_outcome(memory, used=True, outcome=UsageOutcome.success, deltas=DELTAS)
    assert memory.utility_score == 0.6
    assert memory.strength == 0.55
    assert memory.successful_use_count == 1
    assert memory.confidence == 0.5  # untouched -- invariant 2/3


def test_failed_use_lowers_utility_not_confidence():
    memory = make_memory()
    apply_outcome(memory, used=True, outcome=UsageOutcome.failure, deltas=DELTAS)
    assert memory.utility_score == 0.45
    assert memory.failed_use_count == 1
    assert memory.confidence == 0.5


def test_retrieved_but_unused_slightly_lowers_utility():
    memory = make_memory()
    apply_outcome(memory, used=False, outcome=UsageOutcome.neutral, deltas=DELTAS)
    assert memory.utility_score == 0.49
    assert memory.successful_use_count == 0
    assert memory.failed_use_count == 0


def test_utility_and_strength_are_clamped_to_0_1():
    memory = make_memory(utility_score=0.95, strength=0.98)
    apply_outcome(memory, used=True, outcome=UsageOutcome.success, deltas=DELTAS)
    assert memory.utility_score == 1.0
    assert memory.strength == 1.0


def test_confirmation_raises_confidence_only():
    memory = make_memory()
    apply_confirmation(memory, DELTAS)
    assert memory.confidence == 0.6
    assert memory.utility_score == 0.5
    assert memory.strength == 0.5


def test_correction_lowers_confidence_only():
    memory = make_memory()
    apply_correction(memory, DELTAS)
    assert memory.confidence == 0.25
    assert memory.utility_score == 0.5
    assert memory.strength == 0.5


def test_repeated_success_does_not_increase_truth_confidence():
    """Core rule from guide section 29 ('Over-Reinforcement'): usage alone
    must never increase truth confidence -- only utility/strength."""
    memory = make_memory(confidence=0.5)
    for _ in range(20):
        apply_outcome(memory, used=True, outcome=UsageOutcome.success, deltas=DELTAS)
    assert memory.confidence == 0.5
    assert memory.utility_score == 1.0
