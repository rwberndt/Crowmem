from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.scoring_config import ScoringConfig, get_scoring_config
from app.embeddings.base import EmbeddingClient
from app.embeddings.fastembed_client import get_embedding_client
from app.schemas.events import EventCreate, EventResponse
from app.services.extraction_service import extract_and_store_memories
from app.services.ingestion_service import ingest_event

router = APIRouter(tags=["events"])


@router.post("/events", response_model=EventResponse, status_code=201)
def create_event(
    event: EventCreate,
    db: Session = Depends(get_db),
    embedding_client: EmbeddingClient = Depends(get_embedding_client),
    scoring_config: ScoringConfig = Depends(get_scoring_config),
) -> EventResponse:
    episode = ingest_event(db, embedding_client, event, scoring_config)
    if episode.encoded:
        extract_and_store_memories(db, embedding_client, episode, scoring_config)
    return EventResponse.model_validate(episode)
