"""Periodic strength decay (guide section 19). Idempotent: each run only
decays by the time elapsed since a memory's own last_decayed_at, so running
it twice in a row with no time passing is a no-op.

Usage: python -m app.jobs.decay_memories
"""

from datetime import datetime, timezone

import app.models  # noqa: F401 -- registers every model on Base.metadata
from app.core.db import get_session_factory
from app.core.scoring_config import get_scoring_config
from app.repositories.memory_repository import MemoryRepository
from app.services.decay_service import decay_memory


def run_decay_job() -> int:
    session_factory = get_session_factory()
    db = session_factory()
    try:
        config = get_scoring_config().decay
        repo = MemoryRepository(db)
        memories = repo.list_all()
        now = datetime.now(timezone.utc)
        for memory in memories:
            decay_memory(memory, now, config)
        db.commit()
        return len(memories)
    finally:
        db.close()


if __name__ == "__main__":
    count = run_decay_job()
    print(f"Decayed {count} memories.")
