"""Rule-based salience signals (guide section 8): risk, surprise,
future_utility, decision_importance, task_relevance, user_correction.

These begin as keyword/metadata rules per the guide ("this can begin as
rules... later combine rules + classifier") — no LLM call here, so the
salience gate stays cheap, fast, and fully deterministic/testable.
"""

RISK_KEYWORDS: dict[str, float] = {
    "production": 0.9,
    "prod": 0.9,
    "security": 0.9,
    "credential": 0.95,
    "secret": 0.9,
    "password": 0.9,
    "payment": 0.85,
    "permission": 0.7,
    "data loss": 0.95,
    "destructive": 0.9,
    "drop table": 0.95,
    "delete": 0.6,
    "truncate": 0.9,
    "migration failed": 0.85,
    "migrate dev": 0.8,
    "outage": 0.9,
    "rm -rf": 0.95,
}

SURPRISE_EVENT_TYPES: dict[str, float] = {
    "tool_error": 0.8,
    "test_failure": 0.8,
    "deployment_failure": 0.85,
    "user_correction": 0.9,
    "unexpected_result": 0.75,
    "tool_success": 0.2,
    "observation": 0.3,
    "decision": 0.4,
}

FUTURE_UTILITY_KEYWORDS: dict[str, float] = {
    "never": 0.8,
    "always": 0.6,
    "must": 0.7,
    "constraint": 0.8,
    "require": 0.6,
    "deploy": 0.7,
    "migration": 0.7,
    "preference": 0.6,
    "decision": 0.65,
    "workaround": 0.7,
    "shortcut": 0.6,
}

LOW_UTILITY_EVENT_TYPES: dict[str, float] = {
    "file_read": 0.05,
    "list_dir": 0.05,
    "ordinary_command": 0.1,
}

CODE_CHANGE_FUTURE_UTILITY = 0.6


def _keyword_score(text: str, table: dict[str, float]) -> float:
    lowered = text.lower()
    matched = [score for keyword, score in table.items() if keyword in lowered]
    return max(matched) if matched else 0.0


def compute_risk(content: str, metadata: dict) -> float:
    haystack = content + " " + " ".join(str(v) for v in metadata.values())
    return _keyword_score(haystack, RISK_KEYWORDS)


def compute_surprise(event_type: str, metadata: dict) -> float:
    if metadata.get("expected") is False:
        return 0.8
    return SURPRISE_EVENT_TYPES.get(event_type, 0.3)


def compute_future_utility(content: str, event_type: str, metadata: dict) -> float:
    if event_type in LOW_UTILITY_EVENT_TYPES:
        return LOW_UTILITY_EVENT_TYPES[event_type]
    if event_type == "code_change":
        return max(CODE_CHANGE_FUTURE_UTILITY, _keyword_score(content, FUTURE_UTILITY_KEYWORDS))
    return _keyword_score(content, FUTURE_UTILITY_KEYWORDS)


def compute_decision_importance(event_type: str, metadata: dict) -> float:
    if metadata.get("decision") is True or event_type == "decision":
        return 0.8
    return 0.2


def compute_task_relevance(metadata: dict) -> float:
    """Heuristic default (no goal_state required on /events): score rises
    with how much task/environment/tool context the event itself carries.
    """
    specificity_keys = ("environment", "tool", "task", "project")
    present = sum(1 for key in specificity_keys if metadata.get(key))
    return min(1.0, present / len(specificity_keys) + 0.1)


def compute_user_correction(event_type: str) -> float:
    return 1.0 if event_type == "user_correction" else 0.0
