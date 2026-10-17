from app.services import extraction_service
from app.schemas.extraction import MemoryCandidate, MemoryExtractionResult
from tests.fixtures.fake_llm_client import empty_belief_result, make_memory_extractor

CANDIDATE = MemoryCandidate(
    content="Never run `prisma migrate dev` against production; use `prisma migrate deploy`.",
    memory_type="warning",
    risk_score=0.95,
    confidence=0.9,
    associations={"environment": "production", "tool": "prisma", "task": "database_migration"},
)


def _post_production_failure(client):
    return client.post(
        "/events",
        json={
            "content": "Running prisma migrate dev failed because production contains existing migrations.",
            "event_type": "tool_error",
            "project_id": "peach",
            "metadata": {"environment": "production", "tool": "prisma", "task": "database_migration"},
        },
    )


def test_encoded_event_creates_a_memory_with_associations_and_evidence(client, monkeypatch):
    monkeypatch.setattr(extraction_service, "extract_memories", make_memory_extractor(CANDIDATE))
    monkeypatch.setattr(extraction_service, "extract_belief_candidates", empty_belief_result)

    resp = _post_production_failure(client)
    assert resp.status_code == 201

    memories = client.get("/memories", params={"project_id": "peach"}).json()
    assert len(memories) == 1
    assert memories[0]["memory_type"] == "warning"
    assert memories[0]["protected"] is True  # risk_score 0.95 >= 0.85


def test_repeated_identical_candidate_reinforces_instead_of_duplicating(client, monkeypatch):
    monkeypatch.setattr(extraction_service, "extract_memories", make_memory_extractor(CANDIDATE))
    monkeypatch.setattr(extraction_service, "extract_belief_candidates", empty_belief_result)

    _post_production_failure(client)
    _post_production_failure(client)
    _post_production_failure(client)

    memories = client.get("/memories", params={"project_id": "peach"}).json()
    assert len(memories) == 1  # deduplicated, not three copies (guide section 10 / "Memory Flooding")
    assert memories[0]["strength"] > 1.0 - 1e-9 or memories[0]["strength"] == 1.0  # reinforced, clamped at 1.0


def test_ordinary_event_creates_no_memory(client, monkeypatch):
    from tests.fixtures.fake_llm_client import empty_memory_result

    monkeypatch.setattr(extraction_service, "extract_memories", empty_memory_result)
    monkeypatch.setattr(extraction_service, "extract_belief_candidates", empty_belief_result)

    client.post("/events", json={"content": "Opened README.md", "event_type": "file_read", "project_id": "peach"})

    memories = client.get("/memories", params={"project_id": "peach"}).json()
    assert memories == []
