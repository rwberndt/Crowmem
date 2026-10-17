"""Guide section 28, "Belief + Episodic Integration": episodic memory
(raw events) and semantic belief memory (subject/predicate/object with
temporal validity) answer different questions about the same history --
"what do we use now" vs "what did we use before" vs "why did we switch"."""

from app.schemas.extraction import BeliefCandidate, BeliefRelationClassification
from app.services import belief_resolver, extraction_service
from tests.fixtures.fake_llm_client import empty_memory_result, make_belief_extractor


def test_demo_3_current_and_historical_beliefs_both_remain_queryable(client, monkeypatch):
    monkeypatch.setattr(extraction_service, "extract_memories", empty_memory_result)

    monkeypatch.setattr(
        extraction_service, "extract_belief_candidates",
        make_belief_extractor(BeliefCandidate(subject="Peach", predicate="payment_provider", object="Stripe", confidence=0.9)),
    )
    oct1 = client.post(
        "/events", json={"content": "Peach uses Stripe for payments.", "event_type": "observation", "project_id": "peach"}
    ).json()

    monkeypatch.setattr(
        extraction_service, "extract_belief_candidates",
        make_belief_extractor(BeliefCandidate(subject="Peach", predicate="payment_provider", object="Asaas", confidence=0.95)),
    )
    monkeypatch.setattr(
        belief_resolver, "classify_belief_relation",
        lambda *a, **k: BeliefRelationClassification(relation="SUPERSEDES", confidence=0.92, rationale="migration decision"),
    )
    client.post(
        "/events",
        json={"content": "Decision: migrate from Stripe to Asaas; migration completed.", "event_type": "decision", "project_id": "peach"},
    )

    # "What payment provider do we use?" -> Asaas
    current = client.get("/beliefs", params={"subject": "Peach", "predicate": "payment_provider", "status": "active"}).json()
    assert [b["object"] for b in current] == ["Asaas"]

    # "What did we use before?" -> Stripe (preserved, not deleted)
    historical = client.get("/beliefs", params={"subject": "Peach", "predicate": "payment_provider", "status": "superseded"}).json()
    assert [b["object"] for b in historical] == ["Stripe"]

    # "Why did we switch?" -> retrieve episodes around the migration decision;
    # the original Stripe episode remains available, unmodified, even though
    # the belief it supported has since been superseded.
    episodes = client.get("/episodes", params={"project_id": "peach"}).json()
    assert any(e["id"] == oct1["id"] and e["content"] == "Peach uses Stripe for payments." for e in episodes)
