"""Guide section 27, "Second Demo — Learning From Utility": three memories
start on equal footing. Across repeated production migrations, B is used
successfully every time, A is occasionally relevant, C is never useful.
Expected evolution: B's utility/strength rise, A stays roughly stable, C's
utility falls -- and working memory ends up preferring B.

This composes the already-unit-tested pure functions (reinforcement_service,
decay_service, activation_service) into the guide's documented scenario,
rather than re-testing each formula in isolation.
"""

import uuid
from datetime import datetime, timedelta, timezone

from app.models.association import Association
from app.models.enums import MemoryType, UsageOutcome
from app.models.memory import Memory
from app.services.activation_service import compute_activation
from app.services.decay_service import decay_memory
from app.services.reinforcement_service import apply_outcome

GOAL_PAIRS = {("environment", "production"), ("task", "database_migration"), ("tool", "prisma")}


def make_memory(content: str, risk_score: float) -> Memory:
    return Memory(
        id=uuid.uuid4(), content=content, memory_type=MemoryType.fact, project_id="peach",
        created_at=datetime.now(timezone.utc) - timedelta(days=30), strength=0.5, utility_score=0.5,
        risk_score=risk_score, confidence=0.7, retrieval_count=0, successful_use_count=0, failed_use_count=0,
        decay_rate=0.03, protected=False, embedding=None, last_accessed_at=None, last_decayed_at=None,
    )


def test_repeated_usefulness_shifts_ranking_toward_the_useful_memory(scoring_config):
    memory_a = make_memory("Production uses AWS.", risk_score=0.3)  # occasionally relevant
    memory_b = make_memory("Never run `prisma migrate dev` in production.", risk_score=0.9)  # always useful
    memory_c = make_memory("README was edited last Tuesday.", risk_score=0.0)  # never useful

    associations = {
        memory_a.id: [Association(memory_id=memory_a.id, key="environment", value="production", weight=1.0)],
        memory_b.id: [
            Association(memory_id=memory_b.id, key="environment", value="production", weight=1.0),
            Association(memory_id=memory_b.id, key="task", value="database_migration", weight=1.0),
            Association(memory_id=memory_b.id, key="tool", value="prisma", weight=1.0),
        ],
        memory_c.id: [],
    }

    deltas = scoring_config.reinforcement.deltas
    decay_config = scoring_config.decay

    now = datetime.now(timezone.utc) - timedelta(days=30)
    for round_num in range(10):
        now = now + timedelta(days=3)

        apply_outcome(memory_b, used=True, outcome=UsageOutcome.success, deltas=deltas)
        if round_num % 3 == 0:
            apply_outcome(memory_a, used=True, outcome=UsageOutcome.success, deltas=deltas)
        else:
            apply_outcome(memory_a, used=False, outcome=UsageOutcome.neutral, deltas=deltas)
        apply_outcome(memory_c, used=False, outcome=UsageOutcome.neutral, deltas=deltas)

        for memory in (memory_a, memory_b, memory_c):
            decay_memory(memory, now, decay_config)

    # Expected evolution (guide section 27):
    assert memory_b.utility_score > 0.5  # B utility UP
    assert memory_b.strength >= 0.5  # B strength held/UP (reinforcement offsets decay)
    assert memory_c.utility_score < 0.5  # C utility DOWN
    assert memory_c.strength < memory_b.strength  # C weaker than B
    assert memory_a.utility_score < memory_b.utility_score  # A less reinforced than B

    weights = scoring_config.activation.weights
    breakdown_a = compute_activation(memory_a, [], GOAL_PAIRS, associations[memory_a.id], weights, 14)
    breakdown_b = compute_activation(memory_b, [], GOAL_PAIRS, associations[memory_b.id], weights, 14)
    breakdown_c = compute_activation(memory_c, [], GOAL_PAIRS, associations[memory_c.id], weights, 14)

    # Working memory now prefers B over both A and C for this goal.
    assert breakdown_b.activation > breakdown_a.activation
    assert breakdown_b.activation > breakdown_c.activation
