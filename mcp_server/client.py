"""Thin HTTP client to the Corvid FastAPI service. Deliberately the only
way this process touches memory state -- it never imports the `app`
package, so the MCP server stays a stateless process with the FastAPI
service as the single owner of DB state (plan decision: MCP transport is
HTTP, not an in-process import).
"""

import os

import httpx

DEFAULT_BASE_URL = os.environ.get("CORVID_API_BASE_URL", "http://localhost:8000")


class CorvidClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL) -> None:
        self._base_url = base_url

    async def remember_event(
        self,
        content: str,
        event_type: str,
        project_id: str,
        agent_id: str | None = None,
        source: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        payload = {
            "content": content,
            "event_type": event_type,
            "project_id": project_id,
            "agent_id": agent_id,
            "source": source,
            "metadata": metadata or {},
        }
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30) as client:
            resp = await client.post("/events", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def recall_memories(
        self,
        query: str,
        goal_state: dict,
        max_memories: int | None = None,
        max_tokens: int | None = None,
    ) -> dict:
        payload = {"query": query, "goal_state": goal_state, "max_memories": max_memories, "max_tokens": max_tokens}
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30) as client:
            resp = await client.post("/recall", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def report_outcome(
        self,
        retrieval_id: str,
        outcome: str,
        used_memory_ids: list[str],
        reward: float | None = None,
    ) -> dict:
        payload = {"retrieval_id": retrieval_id, "outcome": outcome, "used_memory_ids": used_memory_ids, "reward": reward}
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30) as client:
            resp = await client.post("/outcomes", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def confirm_memory(self, memory_id: str, note: str | None = None) -> dict:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30) as client:
            resp = await client.patch(f"/memories/{memory_id}/confirm", json={"note": note})
            resp.raise_for_status()
            return resp.json()

    async def correct_memory(self, memory_id: str, note: str | None = None) -> dict:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30) as client:
            resp = await client.patch(f"/memories/{memory_id}/correct", json={"note": note})
            resp.raise_for_status()
            return resp.json()

    async def query_beliefs(
        self, subject: str | None = None, predicate: str | None = None, status: str | None = None
    ) -> list[dict]:
        params = {k: v for k, v in {"subject": subject, "predicate": predicate, "status": status}.items() if v}
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30) as client:
            resp = await client.get("/beliefs", params=params)
            resp.raise_for_status()
            return resp.json()
