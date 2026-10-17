from app.models.enums import UsageOutcome
from app.models.memory import Memory


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def apply_outcome(memory: Memory, used: bool, outcome: UsageOutcome, deltas: dict[str, float]) -> None:
    """Reinforcement (guide section 18). Only ever touches utility_score,
    strength, and the use counters -- never `confidence`. Confidence changes
    only via apply_confirmation/apply_correction below, an explicit,
    disjoint path. This separation is how guide invariants 2/3 hold:
    retrieval success strengthens *utility* (how easy this memory is to
    find again), never *truth confidence*.
    """
    if used and outcome == UsageOutcome.success:
        memory.utility_score += deltas["success_used_utility"]
        memory.strength += deltas["success_used_strength"]
        memory.successful_use_count += 1
    elif used and outcome == UsageOutcome.failure:
        memory.utility_score += deltas["failure_used_utility"]
        memory.failed_use_count += 1
    elif not used:
        memory.utility_score += deltas["unused_utility"]

    memory.utility_score = _clamp(memory.utility_score)
    memory.strength = _clamp(memory.strength)


def apply_confirmation(memory: Memory, deltas: dict[str, float]) -> None:
    memory.confidence = _clamp(memory.confidence + deltas["confirm_confidence"])


def apply_correction(memory: Memory, deltas: dict[str, float]) -> None:
    memory.confidence = _clamp(memory.confidence + deltas["correct_confidence"])
