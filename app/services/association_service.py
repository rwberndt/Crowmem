from app.models.association import Association


def compute_context_match(goal_pairs: set[tuple[str, str]], associations: list[Association]) -> float:
    """Fraction of a memory's association weight that matches the current
    goal/context (guide section 15). This is what lets a memory activate
    even when the query text shares no words with it."""
    if not associations:
        return 0.0
    total_weight = sum(a.weight for a in associations)
    if total_weight <= 0:
        return 0.0
    matched_weight = sum(a.weight for a in associations if (a.key, a.value) in goal_pairs)
    return min(1.0, matched_weight / total_weight)


def matched_association_reasons(goal_pairs: set[tuple[str, str]], associations: list[Association]) -> list[str]:
    return [f"{a.key}_match" for a in associations if (a.key, a.value) in goal_pairs]
