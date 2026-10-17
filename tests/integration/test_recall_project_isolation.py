from app.schemas.extraction import MemoryCandidate
from app.services import extraction_service
from tests.fixtures.fake_llm_client import empty_belief_result, make_memory_extractor


def _seed_memory(client, monkeypatch, project_id: str):
    monkeypatch.setattr(
        extraction_service, "extract_memories",
        make_memory_extractor(MemoryCandidate(
            content="Never run `prisma migrate dev` against production; use `prisma migrate deploy`.",
            memory_type="warning", risk_score=0.95, confidence=0.9,
            associations={"environment": "production", "tool": "prisma", "task": "database_migration"},
        )),
    )
    monkeypatch.setattr(extraction_service, "extract_belief_candidates", empty_belief_result)
    client.post(
        "/events",
        json={
            "content": "Running prisma migrate dev failed because production contains existing migrations.",
            "event_type": "tool_error", "project_id": project_id,
            "metadata": {"environment": "production", "tool": "prisma", "task": "database_migration"},
        },
    )


def test_association_matched_memory_does_not_leak_across_projects(client, monkeypatch):
    """Regression test: a memory's associations (environment=production,
    tool=prisma, task=database_migration) are generic enough to match a
    goal_state in an entirely different project. The association-match
    retrieval channel must still be scoped by project_id."""
    _seed_memory(client, monkeypatch, "project-alpha")

    resp = client.post(
        "/recall",
        json={
            "query": "prepare the migration",
            "goal_state": {"project": "project-beta", "environment": "production", "task": "database_migration", "active_tools": ["prisma"]},
        },
    )
    assert resp.json()["working_memory"] == []


def test_same_memory_is_retrievable_within_its_own_project(client, monkeypatch):
    _seed_memory(client, monkeypatch, "project-alpha")

    resp = client.post(
        "/recall",
        json={
            "query": "prepare the migration",
            "goal_state": {"project": "project-alpha", "environment": "production", "task": "database_migration", "active_tools": ["prisma"]},
        },
    )
    assert len(resp.json()["working_memory"]) == 1
