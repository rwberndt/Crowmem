from app.llm.anthropic_client import classify_belief_relation
from app.models.belief import Belief
from app.models.enums import BeliefRelation, BeliefStatus
from app.models.episode import Episode
from app.models.evidence import Evidence
from app.repositories.belief_repository import BeliefRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.schemas.extraction import BeliefCandidate, LlmUsage

CONFIDENCE_PENALTY_ON_DISPUTE = 0.2


def resolve_belief_candidate(
    belief_repo: BeliefRepository,
    evidence_repo: EvidenceRepository,
    episode: Episode,
    candidate: BeliefCandidate,
) -> tuple[Belief, LlmUsage | None]:
    """Belief consolidation with temporal supersession (guide section 11).
    Every belief write happens alongside an Evidence row in the same
    transaction (guide invariant 4). The LLM only classifies the relation
    between two existing belief statements -- it never decides the state
    transition itself (guide invariant 6); that's applied deterministically
    below.

    Returns the usage alongside the belief so the caller can log real spend;
    usage is None when no LLM call was needed (new fact, or an identical
    restatement short-circuited straight to SUPPORTS).
    """
    usage: LlmUsage | None = None
    existing = belief_repo.find_active(episode.project_id, candidate.subject, candidate.predicate)

    if existing is None:
        belief = Belief(
            project_id=episode.project_id,
            subject=candidate.subject,
            predicate=candidate.predicate,
            object=candidate.object,
            confidence=candidate.confidence,
            status=BeliefStatus.active,
            valid_from=episode.observed_at,
        )
        belief_repo.create(belief)

    elif existing.object == candidate.object:
        # Identical fact restated: SUPPORTS, no LLM call needed.
        existing.confidence = min(1.0, existing.confidence + 0.05)
        belief = existing

    else:
        classification, usage = classify_belief_relation(
            candidate.subject, candidate.predicate, existing.object, candidate.object
        )

        if classification.relation in (BeliefRelation.SUPERSEDES, BeliefRelation.REFINES):
            existing.status = BeliefStatus.superseded
            existing.valid_to = episode.observed_at

            new_belief = Belief(
                project_id=episode.project_id,
                subject=candidate.subject,
                predicate=candidate.predicate,
                object=candidate.object,
                confidence=classification.confidence,
                status=BeliefStatus.active,
                valid_from=episode.observed_at,
                relation=classification.relation,
            )
            belief_repo.create(new_belief)
            existing.superseded_by_id = new_belief.id
            belief = new_belief

        elif classification.relation == BeliefRelation.SUPPORTS:
            existing.confidence = min(1.0, existing.confidence + 0.05)
            belief = existing

        else:  # CONTRADICTS: no auto-resolution, leave both for more evidence.
            existing.status = BeliefStatus.disputed
            existing.confidence = max(0.0, existing.confidence - CONFIDENCE_PENALTY_ON_DISPUTE)

            belief = Belief(
                project_id=episode.project_id,
                subject=candidate.subject,
                predicate=candidate.predicate,
                object=candidate.object,
                confidence=max(0.0, classification.confidence - CONFIDENCE_PENALTY_ON_DISPUTE),
                status=BeliefStatus.disputed,
                valid_from=episode.observed_at,
                relation=classification.relation,
            )
            belief_repo.create(belief)

    evidence_repo.create(
        Evidence(
            episode_id=episode.id,
            belief_id=belief.id,
            weight=1.0,
            extraction_confidence=candidate.confidence,
        )
    )
    return belief, usage
