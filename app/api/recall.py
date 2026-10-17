from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.scoring_config import ScoringConfig, get_scoring_config
from app.embeddings.base import EmbeddingClient
from app.embeddings.fastembed_client import get_embedding_client
from app.repositories.retrieval_repository import RetrievalRepository
from app.schemas.recall import RecallRequest, RecallResponse, WorkingMemoryItem
from app.services.retrieval_service import gather_and_score_candidates
from app.services.working_memory_service import persist_retrieval, select_working_memory

router = APIRouter(tags=["recall"])


@router.post("/recall", response_model=RecallResponse)
def recall(
    request: RecallRequest,
    db: Session = Depends(get_db),
    embedding_client: EmbeddingClient = Depends(get_embedding_client),
    scoring_config: ScoringConfig = Depends(get_scoring_config),
) -> RecallResponse:
    if not request.goal_state.project:
        raise HTTPException(status_code=400, detail="goal_state.project is required")

    candidates = gather_and_score_candidates(
        db=db,
        embedding_client=embedding_client,
        project_id=request.goal_state.project,
        query=request.query,
        goal_state=request.goal_state,
        activation_config=scoring_config.activation,
    )

    max_slots = request.max_memories or scoring_config.working_memory.max_slots
    max_tokens = request.max_tokens or scoring_config.working_memory.max_tokens
    slots = select_working_memory(
        candidates,
        max_slots=max_slots,
        max_tokens=max_tokens,
        diversity_penalty_weight=scoring_config.activation.diversity_penalty_weight,
    )

    retrieval_repo = RetrievalRepository(db)
    log = persist_retrieval(retrieval_repo, request.query, request.goal_state.model_dump(), slots)
    db.commit()

    return RecallResponse(
        retrieval_id=log.id,
        working_memory=[
            WorkingMemoryItem(
                id=slot.memory.id,
                content=slot.memory.content,
                activation=slot.breakdown.activation,
                reason=slot.breakdown.reasons,
            )
            for slot in slots
        ],
    )
