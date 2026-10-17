import math
from dataclasses import dataclass
from datetime import datetime, timezone

from app.models.memory import Memory
from app.models.memory_usage import MemoryUsage
from app.models.retrieval_log import RetrievalLog
from app.repositories.retrieval_repository import RetrievalRepository
from app.services.activation_service import ActivationBreakdown
from app.services.novelty_service import cosine_similarity


@dataclass
class WorkingMemorySlot:
    memory: Memory
    breakdown: ActivationBreakdown
    effective_score: float


def estimate_tokens(text: str) -> int:
    """Rough heuristic (~4 chars/token); good enough for budget filtering,
    not meant to match any specific tokenizer exactly."""
    return max(1, len(text) // 4)


def select_working_memory(
    candidates: list[tuple[Memory, ActivationBreakdown]],
    max_slots: int,
    max_tokens: int,
    diversity_penalty_weight: float,
) -> list[WorkingMemorySlot]:
    """Greedy, MMR-style selection (guide sections 16-17): at each step pick
    the candidate with the highest activation/log(1+token_cost), penalized by
    its similarity to slots already chosen, so near-duplicate memories don't
    all occupy the same bounded working memory (guide invariant 7, the
    "context pollution" failure mode in section 29).
    """
    remaining = list(candidates)
    selected: list[WorkingMemorySlot] = []
    selected_embeddings: list[list[float]] = []
    total_tokens = 0

    while remaining and len(selected) < max_slots:
        best_slot: WorkingMemorySlot | None = None
        best_token_cost = 0

        for memory, breakdown in remaining:
            token_cost = estimate_tokens(memory.content)
            if selected and total_tokens + token_cost > max_tokens:
                continue

            interference = 0.0
            if memory.embedding is not None:
                for other_embedding in selected_embeddings:
                    interference = max(interference, cosine_similarity(memory.embedding, other_embedding))

            penalized = breakdown.activation - diversity_penalty_weight * interference
            effective = penalized / math.log(1 + token_cost) if token_cost > 0 else penalized

            if best_slot is None or effective > best_slot.effective_score:
                best_slot = WorkingMemorySlot(memory=memory, breakdown=breakdown, effective_score=effective)
                best_token_cost = token_cost

        if best_slot is None or best_slot.effective_score <= 0:
            break

        selected.append(best_slot)
        if best_slot.memory.embedding is not None:
            selected_embeddings.append(best_slot.memory.embedding)
        total_tokens += best_token_cost
        remaining = [(m, b) for m, b in remaining if m.id != best_slot.memory.id]

    return selected


def persist_retrieval(
    retrieval_repo: RetrievalRepository,
    project_id: str,
    query: str,
    goal_state_dict: dict,
    slots: list[WorkingMemorySlot],
) -> RetrievalLog:
    """Writes the durable, explainable audit trail (guide invariant 10):
    one RetrievalLog row plus one MemoryUsage row per returned memory
    (used=False until /outcomes says otherwise), and bumps each memory's
    retrieval_count/last_accessed_at -- retrieval itself, independent of
    whether the memory turns out to have been useful."""
    now = datetime.now(timezone.utc)

    log = RetrievalLog(
        project_id=project_id,
        query_text=query,
        goal_state=goal_state_dict,
        returned_memory_ids=[str(slot.memory.id) for slot in slots],
        scores_and_reasons={
            str(slot.memory.id): {
                "activation": slot.breakdown.activation,
                "effective_score": slot.effective_score,
                "components": slot.breakdown.components,
                "reasons": slot.breakdown.reasons,
            }
            for slot in slots
        },
    )
    retrieval_repo.create_log(log)

    for slot in slots:
        memory = slot.memory
        memory.retrieval_count += 1
        memory.last_accessed_at = now
        retrieval_repo.create_usage(MemoryUsage(memory_id=memory.id, retrieval_id=log.id, used=False))

    return log
