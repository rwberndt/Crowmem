"""Guide section 26, "Core MVP Demo": a production-migration warning,
learned from one failed + one corrected event, activates for a later goal
that never mentions the original failing command. Demonstrates
context-triggered recall over plain semantic RAG."""

from app.schemas.extraction import MemoryCandidate
from app.services import extraction_service
from tests.fixtures.fake_llm_client import empty_belief_result, make_memory_extractor


def test_demo_1_migration_warning_activates_without_shared_query_wording(client, monkeypatch):
    monkeypatch.setattr(
        extraction_service, "extract_memories",
        make_memory_extractor(MemoryCandidate(
            content="Never run `prisma migrate dev` against production; use `prisma migrate deploy`.",
            memory_type="warning", risk_score=0.95, confidence=0.9,
            associations={"environment": "production", "tool": "prisma", "task": "database_migration"},
        )),
    )
    monkeypatch.setattr(extraction_service, "extract_belief_candidates", empty_belief_result)

    # Event 1: the failure. Event 2 (the discovered fix) is folded into the
    # same extraction call here, matching the guide's single resulting
    # memory -- the pipeline doesn't require a separate event per lesson.
    client.post(
        "/events",
        json={
            "content": "Running prisma migrate dev failed because production contains existing migrations.",
            "event_type": "tool_error", "project_id": "peach",
            "metadata": {"environment": "production", "tool": "prisma", "task": "database_migration"},
        },
    )

    resp = client.post(
        "/recall",
        json={
            "query": "Deploy the API",  # never says "migrate dev"
            "goal_state": {
                "project": "peach", "environment": "production",
                "active_files": ["prisma/schema.prisma"], "active_tools": ["prisma"],
            },
        },
    )

    working_memory = resp.json()["working_memory"]
    assert len(working_memory) == 1
    assert "migrate deploy" in working_memory[0]["content"]
    assert "environment_match" in working_memory[0]["reason"]
