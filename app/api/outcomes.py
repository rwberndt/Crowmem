from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.scoring_config import ScoringConfig, get_scoring_config
from app.repositories.memory_repository import MemoryRepository
from app.repositories.retrieval_repository import RetrievalRepository
from app.schemas.outcomes import OutcomeReport, OutcomeResponse
from app.services.reinforcement_service import apply_outcome

router = APIRouter(tags=["outcomes"])


@router.post("/outcomes", response_model=OutcomeResponse)
def report_outcome(
    report: OutcomeReport,
    db: Session = Depends(get_db),
    scoring_config: ScoringConfig = Depends(get_scoring_config),
) -> OutcomeResponse:
    retrieval_repo = RetrievalRepository(db)
    log = retrieval_repo.get_log(report.retrieval_id)
    if log is None:
        raise HTTPException(status_code=404, detail="retrieval_id not found")

    usage_rows = retrieval_repo.list_usage_for_retrieval(report.retrieval_id)
    memory_repo = MemoryRepository(db)
    used_ids = set(report.used_memory_ids)

    for usage in usage_rows:
        used = usage.memory_id in used_ids
        usage.used = used
        usage.outcome = report.outcome
        usage.reward = report.reward if used else None

        memory = memory_repo.get(usage.memory_id)
        if memory is not None:
            apply_outcome(memory, used, report.outcome, scoring_config.reinforcement.deltas)

    db.commit()
    return OutcomeResponse(retrieval_id=report.retrieval_id, updated_memories=len(usage_rows))
