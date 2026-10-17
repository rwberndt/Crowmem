from sqlalchemy.orm import Session

from app.core.scoring_config import ActivationConfig
from app.embeddings.base import EmbeddingClient
from app.models.memory import Memory
from app.repositories.association_repository import AssociationRepository
from app.repositories.memory_repository import MemoryRepository
from app.schemas.goals import GoalState
from app.services.activation_service import ActivationBreakdown, compute_activation

SEMANTIC_CANDIDATE_LIMIT = 20


def gather_and_score_candidates(
    db: Session,
    embedding_client: EmbeddingClient,
    project_id: str,
    query: str,
    goal_state: GoalState,
    activation_config: ActivationConfig,
) -> list[tuple[Memory, ActivationBreakdown]]:
    """Candidate gathering across channels (guide section 13): semantic
    similarity, association/context matches, and protected high-risk
    memories (always included regardless of score). Belief matches and
    recent-episode channels are left for a later iteration -- none of the
    three guide demos require them, and the memory-only channels above are
    enough to prove goal-conditioned activation over raw semantic search.
    """
    memory_repo = MemoryRepository(db)
    association_repo = AssociationRepository(db)

    # A fresh benchmark store has nothing to retrieve. Avoid loading the
    # embedding model and embedding a long issue prompt on that cold path.
    if not memory_repo.has_any(project_id):
        return []

    query_embedding = embedding_client.embed(query) if query else []
    goal_pairs = set(goal_state.as_context_pairs())

    candidate_ids: dict = {}

    if query_embedding:
        for memory, _distance in memory_repo.semantic_candidates(project_id, query_embedding, SEMANTIC_CANDIDATE_LIMIT):
            candidate_ids[memory.id] = memory

    matched_ids = association_repo.find_memory_ids_matching(project_id, goal_pairs)
    for memory_id in matched_ids:
        if memory_id not in candidate_ids:
            memory = memory_repo.get(memory_id)
            if memory is not None:
                candidate_ids[memory_id] = memory

    for memory in memory_repo.list_protected(project_id):
        candidate_ids.setdefault(memory.id, memory)

    if not candidate_ids:
        return []

    all_associations = association_repo.list_for_memories(list(candidate_ids.keys()))
    associations_by_memory: dict = {}
    for assoc in all_associations:
        associations_by_memory.setdefault(assoc.memory_id, []).append(assoc)

    scored = []
    for memory in candidate_ids.values():
        breakdown = compute_activation(
            memory=memory,
            query_embedding=query_embedding,
            goal_pairs=goal_pairs,
            associations=associations_by_memory.get(memory.id, []),
            weights=activation_config.weights,
            recency_half_life_days=activation_config.recency_half_life_days,
        )
        scored.append((memory, breakdown))

    scored.sort(key=lambda pair: pair[1].activation, reverse=True)
    return scored
