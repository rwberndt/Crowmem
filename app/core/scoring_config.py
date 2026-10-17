from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel

from app.core.config import get_settings


class SalienceConfig(BaseModel):
    weights: dict[str, float]
    thresholds: dict[str, float]


class ActivationConfig(BaseModel):
    weights: dict[str, float]
    diversity_penalty_weight: float
    recency_half_life_days: float


class WorkingMemoryConfig(BaseModel):
    max_slots: int
    max_tokens: int


class ReinforcementConfig(BaseModel):
    deltas: dict[str, float]


class DecayConfig(BaseModel):
    base_rate_by_memory_type: dict[str, float]
    risk_dampening: float
    min_strength_floor_protected: float
    min_strength_floor_default: float


class ScoringConfig(BaseModel):
    salience: SalienceConfig
    activation: ActivationConfig
    working_memory: WorkingMemoryConfig
    reinforcement: ReinforcementConfig
    decay: DecayConfig
    trust_defaults: dict[str, float]


def load_scoring_config(path: str | Path) -> ScoringConfig:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return ScoringConfig.model_validate(raw)


@lru_cache
def get_scoring_config() -> ScoringConfig:
    settings = get_settings()
    return load_scoring_config(settings.scoring_config_path)
