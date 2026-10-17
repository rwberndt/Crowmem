import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.repositories.episode_repository import EpisodeRepository
from app.schemas.episodes import EpisodeResponse

router = APIRouter(tags=["episodes"])


@router.get("/episodes", response_model=list[EpisodeResponse])
def list_episodes(project_id: str, limit: int = 20, db: Session = Depends(get_db)) -> list[EpisodeResponse]:
    """Read-only: episodes are immutable (guide invariant 1), so there is
    deliberately no corresponding create/update route here."""
    repo = EpisodeRepository(db)
    return [EpisodeResponse.model_validate(e) for e in repo.list_recent(project_id, limit)]


@router.get("/episodes/{episode_id}", response_model=EpisodeResponse)
def get_episode(episode_id: uuid.UUID, db: Session = Depends(get_db)) -> EpisodeResponse:
    repo = EpisodeRepository(db)
    episode = repo.get(episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="Episode not found")
    return EpisodeResponse.model_validate(episode)
