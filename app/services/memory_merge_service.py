from app.core.scoring_config import ScoringConfig
from app.embeddings.base import EmbeddingClient
from app.models.association import Association
from app.models.episode import Episode
from app.models.evidence import Evidence
from app.models.memory import Memory
from app.repositories.association_repository import AssociationRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.memory_repository import MemoryRepository
from app.schemas.extraction import MemoryCandidate

# Cosine similarity above this treats a new candidate as a duplicate of an
# existing memory (reinforce) rather than an independent memory (insert).
# Guide section 10 doesn't pin an exact number; MVP keeps this a single
# tunable constant rather than over-building a full refine/contradict
# classifier for raw memories (that nuance is reserved for beliefs, M8).
DEDUP_SIMILARITY_THRESHOLD = 0.90
REINFORCE_STRENGTH_DELTA = 0.05


def merge_or_create_memory(
    memory_repo: MemoryRepository,
    evidence_repo: EvidenceRepository,
    association_repo: AssociationRepository,
    embedding_client: EmbeddingClient,
    episode: Episode,
    candidate: MemoryCandidate,
    scoring_config: ScoringConfig,
) -> Memory:
    embedding = embedding_client.embed(candidate.content)
    similar = memory_repo.find_most_similar(episode.project_id, candidate.memory_type, embedding, limit=1)

    if similar and (1.0 - similar[0][1]) >= DEDUP_SIMILARITY_THRESHOLD:
        memory = similar[0][0]
        memory.strength = min(1.0, memory.strength + REINFORCE_STRENGTH_DELTA)
    else:
        decay_rate = scoring_config.decay.base_rate_by_memory_type.get(candidate.memory_type, 0.02)
        memory = Memory(
            content=candidate.content,
            memory_type=candidate.memory_type,
            project_id=episode.project_id,
            risk_score=candidate.risk_score,
            confidence=candidate.confidence,
            embedding=embedding,
            decay_rate=decay_rate,
            protected=candidate.risk_score >= 0.85,
        )
        memory_repo.create(memory)
        for key, value in candidate.associations.items():
            association_repo.create(Association(memory_id=memory.id, key=key, value=value, weight=1.0))

    evidence_repo.create(
        Evidence(
            episode_id=episode.id,
            memory_id=memory.id,
            weight=1.0,
            extraction_confidence=candidate.confidence,
        )
    )
    return memory
