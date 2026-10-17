from fastapi import APIRouter

from app.jobs.decay_memories import run_decay_job

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/jobs/decay")
def trigger_decay() -> dict[str, int]:
    count = run_decay_job()
    return {"decayed_memories": count}
