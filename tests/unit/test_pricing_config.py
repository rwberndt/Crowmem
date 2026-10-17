from app.core.pricing_config import ModelPricing, PricingConfig


def test_cost_usd_computes_from_per_mtok_rates():
    config = PricingConfig(models={"m": ModelPricing(input_per_mtok=1.0, output_per_mtok=5.0)})
    cost = config.cost_usd("m", input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost == 6.0


def test_cost_usd_is_none_for_unknown_model():
    config = PricingConfig(models={"m": ModelPricing(input_per_mtok=1.0, output_per_mtok=5.0)})
    assert config.cost_usd("unknown-model", input_tokens=100, output_tokens=100) is None
