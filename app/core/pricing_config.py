from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel


class ModelPricing(BaseModel):
    input_per_mtok: float
    output_per_mtok: float


class PricingConfig(BaseModel):
    models: dict[str, ModelPricing]

    def cost_usd(self, model: str, input_tokens: int, output_tokens: int) -> float | None:
        """None means unmeasured/unknown pricing -- callers must treat this
        as "unknown", never coerce it to zero (Mem Off's cost accounting
        explicitly distinguishes the two)."""
        pricing = self.models.get(model)
        if pricing is None:
            return None
        return (input_tokens / 1_000_000) * pricing.input_per_mtok + (output_tokens / 1_000_000) * pricing.output_per_mtok


_PRICING_PATH = Path(__file__).parent.parent.parent / "config" / "llm_pricing.yaml"


@lru_cache
def get_pricing_config() -> PricingConfig:
    with open(_PRICING_PATH, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return PricingConfig.model_validate(raw)
