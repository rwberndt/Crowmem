from dataclasses import dataclass

from app.core.scoring_config import SalienceConfig


@dataclass(frozen=True)
class SalienceSignals:
    novelty: float
    future_utility: float
    task_relevance: float
    risk: float
    surprise: float
    decision_importance: float
    user_correction: float

    def as_dict(self) -> dict[str, float]:
        return {
            "novelty": self.novelty,
            "future_utility": self.future_utility,
            "task_relevance": self.task_relevance,
            "risk": self.risk,
            "surprise": self.surprise,
            "decision_importance": self.decision_importance,
            "user_correction": self.user_correction,
        }


def compute_salience(signals: SalienceSignals, weights: dict[str, float]) -> float:
    """Pure weighted sum (guide section 7). All signal values must already
    be normalized to 0.0 -> 1.0."""
    values = signals.as_dict()
    score = sum(weights.get(key, 0.0) * value for key, value in values.items())
    return max(0.0, min(1.0, score))


class SalienceTier:
    DISCARD = "discard"
    CANDIDATE = "candidate"
    DURABLE = "durable"
    HIGH_PRIORITY = "high_priority"


def classify_salience(score: float, thresholds: dict[str, float]) -> str:
    if score < thresholds["discard"]:
        return SalienceTier.DISCARD
    if score < thresholds["candidate"]:
        return SalienceTier.CANDIDATE
    if score < thresholds["durable"]:
        return SalienceTier.DURABLE
    return SalienceTier.HIGH_PRIORITY


def should_encode(score: float, thresholds: dict[str, float], config: SalienceConfig | None = None) -> bool:
    return classify_salience(score, thresholds) != SalienceTier.DISCARD
