from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.pricing_config import PricingConfig, get_pricing_config
from app.jobs.decay_memories import run_decay_job
from app.services.admin_service import count_project_rows, summarize_usage, wipe_project

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/jobs/decay")
def trigger_decay() -> dict[str, int]:
    count = run_decay_job()
    return {"decayed_memories": count}


@router.delete("/projects/{project_id}")
def wipe(project_id: str, db: Session = Depends(get_db)) -> dict[str, int]:
    """Used by the Mem Off adapter's wipe.sh: empties every project-scoped
    table for this store (episodes, memories, beliefs, retrieval_log,
    usage_log), relying on cascades for their child rows (evidence,
    associations, memory_usage)."""
    return wipe_project(db, project_id)


@router.get("/projects/{project_id}/counts")
def counts(project_id: str, db: Session = Depends(get_db)) -> dict[str, int]:
    """Used by wipe_check.sh: every value must be 0 for the store to count
    as wiped."""
    return count_project_rows(db, project_id)


@router.get("/usage")
def usage(
    project_id: str,
    since: datetime | None = None,
    db: Session = Depends(get_db),
    pricing: PricingConfig = Depends(get_pricing_config),
) -> list[dict]:
    """Used by the Mem Off adapter's usage.sh: this engine's own LLM spend
    since `since` (the adapter tracks its own last-called-at and passes it
    here), one record per call_type/model."""
    return summarize_usage(db, project_id, since, pricing)
