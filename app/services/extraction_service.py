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
    """
    evidence_repo = EvidenceRepository(db)

    memory_result = extract_memories(episode.content, episode.metadata_)
    memories: list[Memory] = []
    if memory_result.memories:
        memory_repo = MemoryRepository(db)
        association_repo = AssociationRepository(db)
        memories = [
            merge_or_create_memory(memory_repo, evidence_repo, association_repo, embedding_client, episode, candidate, scoring_config)
            for candidate in memory_result.memories
        ]

    belief_result = extract_belief_candidates(episode.content, episode.metadata_)
    beliefs: list[Belief] = []
    if belief_result.beliefs:
        belief_repo = BeliefRepository(db)
        beliefs = [
            resolve_belief_candidate(belief_repo, evidence_repo, episode, candidate) for candidate in belief_result.beliefs
        ]

    if memories or beliefs:
        db.commit()
    return memories, beliefs
