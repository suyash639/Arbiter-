"""
arbiter/observability/pricing.py
--------------------------------
Configurable model pricing registry and LLM invocation cost calculation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ModelPricing:
    """Pricing configuration for an LLM model (in USD per 1,000,000 tokens)."""

    input_cost_per_million: float
    output_cost_per_million: float


class ModelPricingRegistry:
    """Registry maintaining pricing metadata across LLM providers and models."""

    DEFAULT_PRICES: Dict[str, ModelPricing] = {
        # Gemini models
        "gemini-3.6-flash": ModelPricing(input_cost_per_million=0.075, output_cost_per_million=0.30),
        "gemini-2.0-flash": ModelPricing(input_cost_per_million=0.10, output_cost_per_million=0.40),
        "gemini-1.5-flash": ModelPricing(input_cost_per_million=0.075, output_cost_per_million=0.30),
        "gemini-1.5-pro": ModelPricing(input_cost_per_million=1.25, output_cost_per_million=5.00),
        # OpenAI models
        "gpt-4o-mini": ModelPricing(input_cost_per_million=0.15, output_cost_per_million=0.60),
        "gpt-4o": ModelPricing(input_cost_per_million=2.50, output_cost_per_million=10.00),
        # Sandbox / Valura model
        "valura-fast": ModelPricing(input_cost_per_million=0.10, output_cost_per_million=0.40),
    }

    def __init__(self, custom_prices: Dict[str, ModelPricing] | None = None) -> None:
        self._prices: Dict[str, ModelPricing] = dict(self.DEFAULT_PRICES)
        if custom_prices:
            self._prices.update(custom_prices)

    def register_price(
        self,
        model_id: str,
        input_cost_per_million: float,
        output_cost_per_million: float,
    ) -> None:
        """Register or override pricing for a specific model."""
        self._prices[model_id.lower().strip()] = ModelPricing(
            input_cost_per_million=input_cost_per_million,
            output_cost_per_million=output_cost_per_million,
        )

    def get_price(self, model_id: str | None) -> ModelPricing | None:
        """Lookup pricing for a model by ID (case-insensitive)."""
        if not model_id:
            return None
        return self._prices.get(model_id.lower().strip())

    def calculate_cost(
        self,
        model_id: str | None,
        input_tokens: int | None,
        output_tokens: int | None,
    ) -> float | None:
        """Calculate estimated cost in USD based on actual token usage.

        Returns None if model pricing is unknown or token counts are unavailable.
        """
        if model_id is None or input_tokens is None or output_tokens is None:
            return None

        price = self.get_price(model_id)
        if price is None:
            return None

        in_cost = (input_tokens * price.input_cost_per_million) / 1_000_000.0
        out_cost = (output_tokens * price.output_cost_per_million) / 1_000_000.0
        return round(in_cost + out_cost, 6)
