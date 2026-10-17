import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.scoring_config import ScoringConfig, get_scoring_config
from app.repositories.memory_repository import MemoryRepository
from app.schemas.memories import MemoryResponse
from app.schemas.outcomes import MemoryConfirmation, MemoryCorrection
from app.services.reinforcement_service import apply_confirmation, apply_correction

router = APIRouter(tags=["memories"])


@router.get("/memories", response_model=list[MemoryResponse])
def list_memories(project_id: str, limit: int = 100, db: Session = Depends(get_db)) -> list[MemoryResponse]:
    repo = MemoryRepository(db)
    return [MemoryResponse.model_validate(m) for m in repo.list_by_project(project_id, limit)]


@router.get("/memories/{memory_id}", response_model=MemoryResponse)
def get_memory(memory_id: uuid.UUID, db: Session = Depends(get_db)) -> MemoryResponse:
    repo = MemoryRepository(db)
    memory = repo.get(memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    return MemoryResponse.model_validate(memory)


@router.patch("/memories/{memory_id}/confirm", response_model=MemoryResponse)
def confirm_memory(
    memory_id: uuid.UUID,
    body: MemoryConfirmation,
    db: Session = Depends(get_db),
    scoring_config: ScoringConfig = Depends(get_scoring_config),
) -> MemoryResponse:
    """Confidence-only path (guide section 18): explicit user confirmation
    raises confidence, never utility/strength -- the inverse separation of
    /outcomes, which only ever touches utility/strength."""
    repo = MemoryRepository(db)
    memory = repo.get(memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    apply_confirmation(memory, scoring_config.reinforcement.deltas)
    db.commit()
    return MemoryResponse.model_validate(memory)


@router.patch("/memories/{memory_id}/correct", response_model=MemoryResponse)
def correct_memory(
    memory_id: uuid.UUID,
    body: MemoryCorrection,
    db: Session = Depends(get_db),
    scoring_config: ScoringConfig = Depends(get_scoring_config),
) -> MemoryResponse:
    repo = MemoryRepository(db)
    memory = repo.get(memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    apply_correction(memory, scoring_config.reinforcement.deltas)
    db.commit()
    return MemoryResponse.model_validate(memory)
