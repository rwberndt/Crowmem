from pydantic import BaseModel, Field


class GoalState(BaseModel):
    """What the agent is currently trying to accomplish (guide section 5.6)."""

    goal: str | None = None
    task: str | None = None
    project: str | None = None
    environment: str | None = None
    active_files: list[str] = Field(default_factory=list)
    active_tools: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    available_actions: list[str] = Field(default_factory=list)

    def as_context_pairs(self) -> list[tuple[str, str]]:
        """Flatten into (key, value) pairs comparable against Association rows."""
        pairs: list[tuple[str, str]] = []
        if self.project:
            pairs.append(("project", self.project))
        if self.task:
            pairs.append(("task", self.task))
        if self.environment:
            pairs.append(("environment", self.environment))
        for tool in self.active_tools:
            pairs.append(("tool", tool))
        for file in self.active_files:
            pairs.append(("file", file))
        return pairs
