import uuid
from datetime import datetime, timedelta, timezone

from app.models.enums import BeliefStatus
from app.models.episode import Episode
from app.repositories.belief_repository import BeliefRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.schemas.extraction import BeliefCandidate, BeliefRelationClassification, LlmUsage
from app.services import belief_resolver

FAKE_USAGE = LlmUsage(model="fake-model", input_tokens=10, output_tokens=5)


def make_episode(db_session, observed_at=None, content="event", embedding=None) -> Episode:
    episode = Episode(
        id=uuid.uuid4(), content=content, event_type="observation", project_id="peach", metadata_={},
        embedding=embedding, observed_at=observed_at or datetime.now(timezone.utc), encoded=True,
    )
    db_session.add(episode)
    db_session.flush()
    return episode


def test_new_belief_created_when_none_exists(db_session):
    belief_repo = BeliefRepository(db_session)
    evidence_repo = EvidenceRepository(db_session)
    episode = make_episode(db_session)

    belief, usage = belief_resolver.resolve_belief_candidate(
        belief_repo, evidence_repo, episode, BeliefCandidate(subject="Peach", predicate="payment_provider", object="Stripe", confidence=0.9)
    )

    assert belief.status == BeliefStatus.active
    assert belief.object == "Stripe"
    assert usage is None  # no LLM call needed for a brand-new fact


def test_identical_restatement_reinforces_without_llm_call(db_session, monkeypatch):
    belief_repo = BeliefRepository(db_session)
    evidence_repo = EvidenceRepository(db_session)
    episode1 = make_episode(db_session)
    episode2 = make_episode(db_session)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("classify_belief_relation should not be called for an identical restatement")

    candidate = BeliefCandidate(subject="Peach", predicate="payment_provider", object="Stripe", confidence=0.9)
    belief_resolver.resolve_belief_candidate(belief_repo, evidence_repo, episode1, candidate)

    monkeypatch.setattr(belief_resolver, "classify_belief_relation", fail_if_called)
    belief, usage = belief_resolver.resolve_belief_candidate(belief_repo, evidence_repo, episode2, candidate)

    assert belief.status == BeliefStatus.active
    assert belief.confidence > 0.9  # reinforced
    assert usage is None


def test_supersession_preserves_old_belief_with_valid_to(db_session, monkeypatch):
    belief_repo = BeliefRepository(db_session)
    evidence_repo = EvidenceRepository(db_session)
    t0 = datetime.now(timezone.utc) - timedelta(days=15)
    t1 = datetime.now(timezone.utc)
    episode1 = make_episode(db_session, observed_at=t0)
    episode2 = make_episode(db_session, observed_at=t1)

    belief_resolver.resolve_belief_candidate(
        belief_repo, evidence_repo, episode1,
        BeliefCandidate(subject="Peach", predicate="payment_provider", object="Stripe", confidence=0.9),
    )

    monkeypatch.setattr(
        belief_resolver, "classify_belief_relation",
        lambda *a, **k: (BeliefRelationClassification(relation="SUPERSEDES", confidence=0.95, rationale="migrated"), FAKE_USAGE),
    )
    new_belief, usage = belief_resolver.resolve_belief_candidate(
        belief_repo, evidence_repo, episode2,
        BeliefCandidate(subject="Peach", predicate="payment_provider", object="Asaas", confidence=0.95),
    )
    assert usage == FAKE_USAGE

    old_belief = belief_repo.find_active("peach", "Peach", "payment_provider")
    assert old_belief is not None
    assert old_belief.object == "Asaas"  # the only *active* one now
    assert new_belief.status == BeliefStatus.active
    assert new_belief.object == "Asaas"

    all_beliefs = belief_repo.list(subject="Peach", predicate="payment_provider")
    stripe = next(b for b in all_beliefs if b.object == "Stripe")
    assert stripe.status == BeliefStatus.superseded
    assert stripe.valid_to == t1
    assert stripe.superseded_by_id == new_belief.id


def test_contradiction_disputes_both_beliefs_without_auto_resolution(db_session, monkeypatch):
    belief_repo = BeliefRepository(db_session)
    evidence_repo = EvidenceRepository(db_session)
    episode1 = make_episode(db_session)
    episode2 = make_episode(db_session)

    belief_resolver.resolve_belief_candidate(
        belief_repo, evidence_repo, episode1,
        BeliefCandidate(subject="Peach", predicate="payment_provider", object="Stripe", confidence=0.9),
    )

    monkeypatch.setattr(
        belief_resolver, "classify_belief_relation",
        lambda *a, **k: (BeliefRelationClassification(relation="CONTRADICTS", confidence=0.6, rationale="unclear"), FAKE_USAGE),
    )
    new_belief, usage = belief_resolver.resolve_belief_candidate(
        belief_repo, evidence_repo, episode2,
        BeliefCandidate(subject="Peach", predicate="payment_provider", object="Asaas", confidence=0.6),
    )
    assert usage == FAKE_USAGE

    old_belief = belief_repo.find_active("peach", "Peach", "payment_provider")
    assert old_belief is None  # neither is active -- no auto-resolution

    all_beliefs = belief_repo.list(subject="Peach", predicate="payment_provider")
    assert all(b.status == BeliefStatus.disputed for b in all_beliefs)
    assert new_belief.status == BeliefStatus.disputed


def test_every_belief_has_evidence(db_session):
    belief_repo = BeliefRepository(db_session)
    evidence_repo = EvidenceRepository(db_session)
    episode = make_episode(db_session)

    belief, _usage = belief_resolver.resolve_belief_candidate(
        belief_repo, evidence_repo, episode,
        BeliefCandidate(subject="Peach", predicate="payment_provider", object="Stripe", confidence=0.9),
    )
    db_session.flush()

    from sqlalchemy import select

    from app.models.evidence import Evidence

    rows = db_session.execute(select(Evidence).where(Evidence.belief_id == belief.id)).scalars().all()
    assert len(rows) >= 1
    assert rows[0].episode_id == episode.id


def test_belief_lookup_does_not_leak_across_projects(db_session):
    """Regression test, same class of bug as the association-matching
    cross-project leak: a belief for one project's subject/predicate must
    not be found as 'active' when looked up under a different project."""
    belief_repo = BeliefRepository(db_session)
    evidence_repo = EvidenceRepository(db_session)
    episode_alpha = make_episode(db_session)
    episode_alpha.project_id = "project-alpha"
    db_session.flush()

    belief_resolver.resolve_belief_candidate(
        belief_repo, evidence_repo, episode_alpha,
        BeliefCandidate(subject="Peach", predicate="payment_provider", object="Stripe", confidence=0.9),
    )

    assert belief_repo.find_active("project-beta", "Peach", "payment_provider") is None
    assert belief_repo.find_active("project-alpha", "Peach", "payment_provider") is not None
