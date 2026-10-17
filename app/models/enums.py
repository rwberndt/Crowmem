import enum


class MemoryType(str, enum.Enum):
    procedural = "procedural"
    failure = "failure"
    constraint = "constraint"
    decision = "decision"
    preference = "preference"
    environment = "environment"
    fact = "fact"
    workflow = "workflow"
    warning = "warning"
    pattern = "pattern"


class BeliefStatus(str, enum.Enum):
    active = "active"
    superseded = "superseded"
    disputed = "disputed"
    inactive = "inactive"


class BeliefRelation(str, enum.Enum):
    # Member names must equal their values: SQLAlchemy's Enum column stores
    # by member *name*, and the Postgres enum labels (belief_relation) are
    # these uppercase strings -- a name/value mismatch here causes DataError
    # on insert (invalid input value for enum belief_relation).
    SUPPORTS = "SUPPORTS"
    SUPERSEDES = "SUPERSEDES"
    CONTRADICTS = "CONTRADICTS"
    REFINES = "REFINES"


class UsageOutcome(str, enum.Enum):
    success = "success"
    failure = "failure"
    neutral = "neutral"
    unknown = "unknown"


class SourceType(str, enum.Enum):
    direct_experience = "direct_experience"
    other_agent = "other_agent"
    user_statement = "user_statement"
    runtime_observation = "runtime_observation"
    documentation = "documentation"
    llm_inference = "llm_inference"
