from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.enums import BeliefStatus
from app.repositories.belief_repository import BeliefRepository
from app.schemas.beliefs import BeliefResponse

router = APIRouter(tags=["beliefs"])


@router.get("/beliefs", response_model=list[BeliefResponse])
def list_beliefs(
    project_id: str | None = None,
    subject: str | None = None,
    predicate: str | None = None,
    status: BeliefStatus | None = None,
    db: Session = Depends(get_db),
) -> list[BeliefResponse]:
    repo = BeliefRepository(db)
    return [BeliefResponse.model_validate(b) for b in repo.list(project_id, subject, predicate, status)]
