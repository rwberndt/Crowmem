from app.schemas.extraction import BeliefCandidate
from app.services import belief_resolver, extraction_service
from tests.fixtures.fake_llm_client import empty_memory_result, make_belief_extractor, make_relation_classifier


def test_belief_supersession_end_to_end_via_api(client, monkeypatch):
    """Reproduces guide demo 3 (section 28) through the public API."""
    monkeypatch.setattr(extraction_service, "extract_memories", empty_memory_result)

    monkeypatch.setattr(
        extraction_service, "extract_belief_candidates",
        make_belief_extractor(BeliefCandidate(subject="Peach", predicate="payment_provider", object="Stripe", confidence=0.9)),
    )
    client.post("/events", json={"content": "Peach uses Stripe for payments.", "event_type": "observation", "project_id": "peach"})

    monkeypatch.setattr(
        extraction_service, "extract_belief_candidates",
        make_belief_extractor(BeliefCandidate(subject="Peach", predicate="payment_provider", object="Asaas", confidence=0.95)),
    )
    monkeypatch.setattr(belief_resolver, "classify_belief_relation", make_relation_classifier("SUPERSEDES", confidence=0.92))
    client.post("/events", json={"content": "Migration from Stripe to Asaas completed.", "event_type": "observation", "project_id": "peach"})

    active = client.get("/beliefs", params={"subject": "Peach", "predicate": "payment_provider", "status": "active"}).json()
    assert len(active) == 1
    assert active[0]["object"] == "Asaas"

    superseded = client.get("/beliefs", params={"subject": "Peach", "predicate": "payment_provider", "status": "superseded"}).json()
    assert len(superseded) == 1
    assert superseded[0]["object"] == "Stripe"
    assert superseded[0]["valid_to"] is not None

    # Historical episodes/beliefs remain available even though the belief changed.
    all_beliefs = client.get("/beliefs", params={"subject": "Peach", "predicate": "payment_provider"}).json()
    assert {b["object"] for b in all_beliefs} == {"Stripe", "Asaas"}
