import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.episode import Episode


class EpisodeRepository:
    """Episodes are immutable: this repository intentionally exposes no
    update/delete methods (guide invariant 1)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, episode: Episode) -> Episode:
        self.db.add(episode)
        self.db.flush()
        return episode

    def get(self, episode_id: uuid.UUID) -> Episode | None:
        return self.db.get(Episode, episode_id)

    def list_recent(self, project_id: str, limit: int = 20) -> list[Episode]:
        stmt = (
            select(Episode)
            .where(Episode.project_id == project_id)
            .order_by(Episode.observed_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars())

    def list_encoded_embeddings(self, project_id: str, limit: int = 200) -> list[Episode]:
        """Recent episodes with embeddings, for novelty comparison."""
        stmt = (
            select(Episode)
            .where(Episode.project_id == project_id, Episode.embedding.is_not(None))
            .order_by(Episode.observed_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars())
