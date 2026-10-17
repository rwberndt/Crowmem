"""MCP tool surface over the Corvid memory engine, for a coding agent (e.g.
Claude Code) to use live during a demo. Every tool is a thin wrapper around
CorvidClient (HTTP to the FastAPI service) -- this module never touches the
database directly.
"""

from typing import Literal

from mcp.server.mcpserver import MCPServer

from mcp_server.client import CorvidClient

mcp = MCPServer("corvid-memory")
client = CorvidClient()


@mcp.tool()
async def remember_event(
    content: str,
    event_type: str,
    project_id: str,
    agent_id: str | None = None,
    metadata: dict | None = None,
) -> dict:
    """Record an observed event (a tool error, a decision, a user correction,
    an outcome, etc.) into the Corvid memory engine. A salience gate decides
    whether this becomes a durable memory -- most routine events are kept
    only as a raw episode and never surface again."""
    return await client.remember_event(content, event_type, project_id, agent_id=agent_id, metadata=metadata)


@mcp.tool()
async def recall_memories(
    query: str,
    project: str,
    task: str | None = None,
    environment: str | None = None,
    active_tools: list[str] | None = None,
    active_files: list[str] | None = None,
    max_memories: int | None = None,
) -> dict:
    """Goal-conditioned recall: returns a small, bounded working memory
    ranked by activation (goal/context match + utility + confidence +
    recency + risk), not just text similarity to `query`. A relevant warning
    can activate even if its wording shares nothing with the query. The
    response includes a `reason` list per memory explaining why it was
    selected, and a `retrieval_id` to pass to report_outcome afterward."""
    goal_state = {
        "project": project,
        "task": task,
        "environment": environment,
        "active_tools": active_tools or [],
        "active_files": active_files or [],
    }
    return await client.recall_memories(query, goal_state, max_memories=max_memories)


@mcp.tool()
async def report_outcome(
    retrieval_id: str,
    outcome: Literal["success", "failure", "neutral", "unknown"],
    used_memory_ids: list[str],
    reward: float | None = None,
) -> dict:
    """Report what happened after acting on a prior recall_memories call.
    This only changes how easily the used memories are found again
    (their utility/strength) -- it never changes whether a memory is
    considered factually true (its confidence). Use confirm_or_correct_memory
    for that."""
    return await client.report_outcome(retrieval_id, outcome, used_memory_ids, reward=reward)


@mcp.tool()
async def confirm_or_correct_memory(
    memory_id: str,
    action: Literal["confirm", "correct"],
    note: str | None = None,
) -> dict:
    """Explicitly confirm a memory as still accurate, or flag it as wrong.
    This changes the memory's confidence only -- independent of how often
    it has been successfully used (utility/strength are a separate axis)."""
    if action == "confirm":
        return await client.confirm_memory(memory_id, note)
    return await client.correct_memory(memory_id, note)


@mcp.tool()
async def query_beliefs(
    subject: str | None = None,
    predicate: str | None = None,
    status: Literal["active", "superseded", "disputed", "inactive"] | None = None,
) -> list[dict]:
    """Query structured beliefs, e.g. 'what payment provider do we use now?'
    (status=active) vs 'what did we use before?' (status=superseded,
    historical beliefs are preserved, never deleted)."""
    return await client.query_beliefs(subject=subject, predicate=predicate, status=status)
