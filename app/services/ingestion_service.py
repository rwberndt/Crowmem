from sqlalchemy.orm import Session

from app.core.scoring_config import ScoringConfig
from app.embeddings.base import EmbeddingClient
from app.models.episode import Episode
from app.repositories.episode_repository import EpisodeRepository
from app.schemas.events import EventCreate
from app.services import risk_service
from app.services.novelty_service import compute_novelty
from app.services.salience_service import SalienceSignals, compute_salience, should_encode


def ingest_event(
    db: Session,
    embedding_client: EmbeddingClient,
    event: EventCreate,
    scoring_config: ScoringConfig,
) -> Episode:
    """Persist an immutable episode, then run it through the salience gate
    (guide sections 7-8) to decide whether it's worth encoding into durable
    memory. Extraction itself (M3) is triggered separately by the caller
    when `episode.encoded` comes back True, so this function stays a single,
    independently testable unit: embed -> compare against existing episodes
    -> score -> persist.
    """
    embedding = embedding_client.embed(event.content)

    repo = EpisodeRepository(db)
    recent = repo.list_encoded_embeddings(event.project_id)
    recent_embeddings = [e.embedding for e in recent if e.embedding is not None]

    signals = SalienceSignals(
        novelty=compute_novelty(embedding, recent_embeddings),
        future_utility=risk_service.compute_future_utility(event.content, event.event_type, event.metadata),
        task_relevance=risk_service.compute_task_relevance(event.metadata),
        risk=risk_service.compute_risk(event.content, event.metadata),
        surprise=risk_service.compute_surprise(event.event_type, event.metadata),
        decision_importance=risk_service.compute_decision_importance(event.event_type, event.metadata),
        user_correction=risk_service.compute_user_correction(event.event_type),
    )
    salience_score = compute_salience(signals, scoring_config.salience.weights)
    encoded = should_encode(salience_score, scoring_config.salience.thresholds)

    episode = Episode(
        content=event.content,
        event_type=event.event_type,
        project_id=event.project_id,
        agent_id=event.agent_id,
        source=event.source,
        metadata_=event.metadata,
        embedding=embedding,
        salience_score=salience_score,
        encoded=encoded,
    )
    repo.create(episode)
    db.commit()
    return episode
