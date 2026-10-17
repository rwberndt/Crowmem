import math
from datetime import datetime, timezone

from app.core.scoring_config import DecayConfig
from app.models.memory import Memory


def effective_decay_rate(memory: Memory, config: DecayConfig) -> float:
    base_rate = config.base_rate_by_memory_type.get(memory.memory_type.value, 0.02)
    return base_rate * (1.0 - config.risk_dampening * memory.risk_score)


def decay_strength(memory: Memory, delta_days: float, config: DecayConfig) -> float:
    """strength(t+1) = max(floor, strength(t) * exp(-effective_decay_rate * dt))
    (guide section 19). Protected memories, and memories whose risk_score
    dampens the effective rate, decay more slowly -- never below their
    configured floor (guide invariant 5 / the "risky forgetting" failure
    mode in section 29)."""
    rate = effective_decay_rate(memory, config)
    floor = config.min_strength_floor_protected if memory.protected else config.min_strength_floor_default
    decayed = memory.strength * math.exp(-rate * max(0.0, delta_days))
    return max(floor, decayed)


def decay_memory(memory: Memory, now: datetime, config: DecayConfig) -> None:
    reference = memory.last_decayed_at or memory.created_at
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    delta_days = max(0.0, (now - reference).total_seconds() / 86400.0)
    memory.strength = decay_strength(memory, delta_days, config)
    memory.last_decayed_at = now
