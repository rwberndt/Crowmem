import math
import uuid
from datetime import datetime, timedelta, timezone

from app.core.scoring_config import DecayConfig
from app.models.enums import MemoryType
from app.models.memory import Memory
from app.services.decay_service import decay_memory, decay_strength, effective_decay_rate

CONFIG = DecayConfig(
    base_rate_by_memory_type={"fact": 0.05, "warning": 0.005, "constraint": 0.002},
    risk_dampening=0.8,
    min_strength_floor_protected=0.4,
    min_strength_floor_default=0.0,
)


def make_memory(**overrides) -> Memory:
    defaults = dict(
        id=uuid.uuid4(), content="x", memory_type=MemoryType.fact, project_id="p",
        created_at=datetime.now(timezone.utc), strength=1.0, utility_score=0.5, risk_score=0.0, confidence=0.5,
        retrieval_count=0, successful_use_count=0, failed_use_count=0, decay_rate=0.02, protected=False,
        embedding=None, last_accessed_at=None, last_decayed_at=None,
    )
    defaults.update(overrides)
    return Memory(**defaults)


def test_high_risk_memory_decays_slower_than_low_risk_memory():
    low_risk = make_memory(memory_type=MemoryType.fact, risk_score=0.0)
    high_risk = make_memory(memory_type=MemoryType.fact, risk_score=0.95)

    rate_low = effective_decay_rate(low_risk, CONFIG)
    rate_high = effective_decay_rate(high_risk, CONFIG)

    assert rate_high < rate_low


def test_protected_memory_never_decays_below_its_floor():
    memory = make_memory(memory_type=MemoryType.warning, risk_score=0.95, protected=True, strength=1.0)
    strength_after_long_time = decay_strength(memory, delta_days=100_000, config=CONFIG)
    assert strength_after_long_time == CONFIG.min_strength_floor_protected


def test_unprotected_memory_can_decay_to_zero_floor():
    memory = make_memory(memory_type=MemoryType.fact, risk_score=0.0, protected=False, strength=1.0)
    strength_after_long_time = decay_strength(memory, delta_days=100_000, config=CONFIG)
    assert strength_after_long_time == CONFIG.min_strength_floor_default


def test_decay_matches_closed_form_exponential():
    memory = make_memory(memory_type=MemoryType.fact, risk_score=0.0, strength=1.0)
    rate = effective_decay_rate(memory, CONFIG)
    expected = math.exp(-rate * 10)
    assert math.isclose(decay_strength(memory, delta_days=10, config=CONFIG), expected, rel_tol=1e-9)


def test_decay_memory_is_idempotent_with_no_elapsed_time():
    now = datetime.now(timezone.utc)
    memory = make_memory(strength=0.8, last_decayed_at=now)
    decay_memory(memory, now, CONFIG)
    assert math.isclose(memory.strength, 0.8, rel_tol=1e-9)


def test_decay_memory_updates_last_decayed_at():
    now = datetime.now(timezone.utc)
    memory = make_memory(strength=1.0, last_decayed_at=now - timedelta(days=5))
    decay_memory(memory, now, CONFIG)
    assert memory.last_decayed_at == now
    assert memory.strength < 1.0
