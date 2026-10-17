from app.schemas.extraction import MemoryCandidate
from app.services import extraction_service
from tests.fixtures.fake_llm_client import empty_belief_result, make_memory_extractor

CANDIDATE = MemoryCandidate(
    content="Never run `prisma migrate dev` against production; use `prisma migrate deploy`.",
    memory_type="warning", risk_score=0.95, confidence=0.9,
    associations={"environment": "production", "tool": "prisma", "task": "database_migration"},
)


def test_wipe_empties_a_project_without_touching_others(client, monkeypatch):
    monkeypatch.setattr(extraction_service, "extract_memories", make_memory_extractor(CANDIDATE))
    monkeypatch.setattr(extraction_service, "extract_belief_candidates", empty_belief_result)

    for project in ("store-a", "store-b"):
        client.post(
            "/events",
            json={
                "content": "Running prisma migrate dev failed because production contains existing migrations.",
                "event_type": "tool_error", "project_id": project,
                "metadata": {"environment": "production", "tool": "prisma", "task": "database_migration"},
            },
        )

    before_a = client.get("/admin/projects/store-a/counts").json()
    assert any(v > 0 for v in before_a.values())

    wipe_resp = client.delete("/admin/projects/store-a")
    assert wipe_resp.status_code == 200

    after_a = client.get("/admin/projects/store-a/counts").json()
    assert all(v == 0 for v in after_a.values())

    # store-b is untouched by store-a's wipe.
    after_b = client.get("/admin/projects/store-b/counts").json()
    assert any(v > 0 for v in after_b.values())
    assert client.get("/memories", params={"project_id": "store-b"}).json() != []


def test_usage_endpoint_reports_cost(client, monkeypatch):
    monkeypatch.setattr(extraction_service, "extract_memories", make_memory_extractor(CANDIDATE))
    monkeypatch.setattr(extraction_service, "extract_belief_candidates", empty_belief_result)

    client.post(
        "/events",
        json={
            "content": "Running prisma migrate dev failed because production contains existing migrations.",
            "event_type": "tool_error", "project_id": "store-usage",
            "metadata": {"environment": "production", "tool": "prisma", "task": "database_migration"},
        },
    )

    usage = client.get("/admin/usage", params={"project_id": "store-usage"}).json()
    assert {r["id"] for r in usage} == {"extract_memories", "extract_belief_candidates"}
    assert all(r["tokens_in"] > 0 for r in usage)
