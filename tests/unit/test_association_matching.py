import uuid

from app.models.association import Association
from app.services.association_service import compute_context_match, matched_association_reasons


def assoc(key, value, weight=1.0):
    return Association(memory_id=uuid.uuid4(), key=key, value=value, weight=weight)


def test_full_context_match_scores_one():
    goal_pairs = {("environment", "production"), ("tool", "prisma"), ("task", "database_migration")}
    associations = [assoc("environment", "production"), assoc("tool", "prisma"), assoc("task", "database_migration")]
    assert compute_context_match(goal_pairs, associations) == 1.0


def test_no_context_match_scores_zero():
    goal_pairs = {("environment", "staging")}
    associations = [assoc("environment", "production")]
    assert compute_context_match(goal_pairs, associations) == 0.0


def test_partial_match_is_weighted_fraction():
    goal_pairs = {("environment", "production")}
    associations = [assoc("environment", "production", weight=1.0), assoc("tool", "prisma", weight=1.0)]
    assert compute_context_match(goal_pairs, associations) == 0.5


def test_memory_with_no_associations_is_neutral_not_undefined():
    assert compute_context_match({("environment", "production")}, []) == 0.0


def test_matched_reasons_lists_each_matching_key():
    goal_pairs = {("environment", "production"), ("tool", "prisma")}
    associations = [assoc("environment", "production"), assoc("tool", "prisma"), assoc("task", "other")]
    reasons = matched_association_reasons(goal_pairs, associations)
    assert "environment_match" in reasons
    assert "tool_match" in reasons
    assert "task_match" not in reasons
