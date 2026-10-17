from sqlalchemy.orm import Session

from app.core.scoring_config import ScoringConfig
from app.embeddings.base import EmbeddingClient
from app.llm.anthropic_client import extract_belief_candidates, extract_memories
from app.models.belief import Belief
from app.models.episode import Episode
from app.models.memory import Memory
from app.repositories.association_repository import AssociationRepository
from app.repositories.belief_repository import BeliefRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.memory_repository import MemoryRepository
from app.repositories.usage_log_repository import UsageLogRepository
from app.services.belief_resolver import resolve_belief_candidate
from app.services.memory_merge_service import merge_or_create_memory


def extract_and_store_memories(
    db: Session,
    embedding_client: EmbeddingClient,
    episode: Episode,
    scoring_config: ScoringConfig,
) -> tuple[list[Memory], list[Belief]]:
    """Only called once salience clears the encode threshold (guide section 9).
    The LLM (app.llm.anthropic_client) only proposes candidates; this function,
    memory_merge_service, and belief_resolver decide insert/reinforce/supersede
    — the LLM never writes to the database directly (guide invariant 6).

    Every LLM call made here is logged via UsageLogRepository regardless of
    whether it produced any candidates -- tokens are spent on the call
    itself, not on its result (Mem Off-style cost accounting treats
    unmeasured spend as unknown, never zero).
    """
    evidence_repo = EvidenceRepository(db)
    usage_repo = UsageLogRepository(db)

    semantic_metadata = {key: value for key, value in episode.metadata_.items() if key != "memory_only"}
    memory_result, memory_usage = extract_memories(episode.content, semantic_metadata)
    usage_repo.record(episode.project_id, "extract_memories", memory_usage)

    memories: list[Memory] = []
    if memory_result.memories:
        memory_repo = MemoryRepository(db)
        association_repo = AssociationRepository(db)
        memories = [
            merge_or_create_memory(memory_repo, evidence_repo, association_repo, embedding_client, episode, candidate, scoring_config)
            for candidate in memory_result.memories
        ]

    beliefs: list[Belief] = []
    # Coding-agent tool observations feed the memory channel used by /recall.
    # They do not need the separate belief extraction call on every tool use.
    if not episode.metadata_.get("memory_only", False):
        belief_result, belief_usage = extract_belief_candidates(episode.content, semantic_metadata)
        usage_repo.record(episode.project_id, "extract_belief_candidates", belief_usage)

        if belief_result.beliefs:
            belief_repo = BeliefRepository(db)
            for candidate in belief_result.beliefs:
                belief, relation_usage = resolve_belief_candidate(belief_repo, evidence_repo, episode, candidate)
                beliefs.append(belief)
                if relation_usage is not None:
                    usage_repo.record(episode.project_id, "classify_belief_relation", relation_usage)

    db.commit()
    return memories, beliefs
