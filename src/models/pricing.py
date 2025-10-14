#region Imports
from dataclasses import dataclass
from typing import Optional
#endregion


#region Constants
# Claude API Pricing (per million tokens)
# Source: https://claude.com/pricing (as of 2025-10-14)

# Opus 4.1 pricing
OPUS_4_INPUT_PRICE = 15.0  # $15 per million tokens
OPUS_4_OUTPUT_PRICE = 75.0  # $75 per million tokens
OPUS_4_CACHE_WRITE_PRICE = 18.75  # $18.75 per million tokens
OPUS_4_CACHE_READ_PRICE = 1.50  # $1.50 per million tokens

# Sonnet 4.5 pricing (simplified - using base rate)
# Note: Real pricing has context length tiers (≤200K vs >200K)
SONNET_4_5_INPUT_PRICE = 3.0  # $3 per million tokens (base rate)
SONNET_4_5_OUTPUT_PRICE = 15.0  # $15 per million tokens (base rate)
SONNET_4_5_CACHE_WRITE_PRICE = 3.75  # $3.75 per million tokens (base rate)
SONNET_4_5_CACHE_READ_PRICE = 0.30  # $0.30 per million tokens (base rate)

# Sonnet 4 pricing
SONNET_4_INPUT_PRICE = 3.0  # $3 per million tokens
SONNET_4_OUTPUT_PRICE = 15.0  # $15 per million tokens
SONNET_4_CACHE_WRITE_PRICE = 3.75  # $3.75 per million tokens
SONNET_4_CACHE_READ_PRICE = 0.30  # $0.30 per million tokens

# Haiku 3.5 pricing
HAIKU_3_5_INPUT_PRICE = 1.0  # $1 per million tokens
HAIKU_3_5_OUTPUT_PRICE = 5.0  # $5 per million tokens
HAIKU_3_5_CACHE_WRITE_PRICE = 1.0  # $1 per million tokens
HAIKU_3_5_CACHE_READ_PRICE = 0.08  # $0.08 per million tokens

# Legacy models (fallback)
LEGACY_INPUT_PRICE = 3.0  # Default: $3 per million tokens
LEGACY_OUTPUT_PRICE = 15.0  # Default: $15 per million tokens
LEGACY_CACHE_WRITE_PRICE = 3.75  # Default: $3.75 per million tokens
LEGACY_CACHE_READ_PRICE = 0.30  # Default: $0.30 per million tokens
#endregion


#region Data Classes


@dataclass(frozen=True)
class ModelPricing:
    """
    Represents pricing for a Claude model.

    Attributes:
        input_price: Price per million input tokens (USD)
        output_price: Price per million output tokens (USD)
        cache_write_price: Price per million cache creation tokens (USD)
        cache_read_price: Price per million cache read tokens (USD)
        model_name: Human-readable model name
    """

    input_price: float
    output_price: float
    cache_write_price: float
    cache_read_price: float
    model_name: str


#endregion


#region Functions


def get_model_pricing(model_id: str) -> ModelPricing:
    """
    Get pricing information for a given model ID.

    Args:
        model_id: Model identifier (e.g., 'claude-opus-4-1-20250805')

    Returns:
        ModelPricing object with pricing details
    """
    model_lower = model_id.lower()

    # Opus 4.x
    if "opus-4" in model_lower:
        return ModelPricing(
            input_price=OPUS_4_INPUT_PRICE,
            output_price=OPUS_4_OUTPUT_PRICE,
            cache_write_price=OPUS_4_CACHE_WRITE_PRICE,
            cache_read_price=OPUS_4_CACHE_READ_PRICE,
            model_name="Opus 4",
        )

    # Sonnet 4.5
    elif "sonnet-4-5" in model_lower or "sonnet-4.5" in model_lower:
        return ModelPricing(
            input_price=SONNET_4_5_INPUT_PRICE,
            output_price=SONNET_4_5_OUTPUT_PRICE,
            cache_write_price=SONNET_4_5_CACHE_WRITE_PRICE,
            cache_read_price=SONNET_4_5_CACHE_READ_PRICE,
            model_name="Sonnet 4.5",
        )

    # Sonnet 4 (not 4.5)
    elif "sonnet-4" in model_lower:
        return ModelPricing(
            input_price=SONNET_4_INPUT_PRICE,
            output_price=SONNET_4_OUTPUT_PRICE,
            cache_write_price=SONNET_4_CACHE_WRITE_PRICE,
            cache_read_price=SONNET_4_CACHE_READ_PRICE,
            model_name="Sonnet 4",
        )

    # Haiku 3.5
    elif "haiku-3-5" in model_lower or "haiku-3.5" in model_lower:
        return ModelPricing(
            input_price=HAIKU_3_5_INPUT_PRICE,
            output_price=HAIKU_3_5_OUTPUT_PRICE,
            cache_write_price=HAIKU_3_5_CACHE_WRITE_PRICE,
            cache_read_price=HAIKU_3_5_CACHE_READ_PRICE,
            model_name="Haiku 3.5",
        )

    # Default/unknown model
    else:
        return ModelPricing(
            input_price=LEGACY_INPUT_PRICE,
            output_price=LEGACY_OUTPUT_PRICE,
            cache_write_price=LEGACY_CACHE_WRITE_PRICE,
            cache_read_price=LEGACY_CACHE_READ_PRICE,
            model_name="Unknown",
        )


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    model_id: str,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> float:
    """
    Calculate the cost for given token usage including cache tokens.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model_id: Model identifier
        cache_creation_tokens: Number of cache creation (write) tokens
        cache_read_tokens: Number of cache read tokens

    Returns:
        Total cost in USD
    """
    pricing = get_model_pricing(model_id)

    input_cost = (input_tokens / 1_000_000) * pricing.input_price
    output_cost = (output_tokens / 1_000_000) * pricing.output_price
    cache_write_cost = (cache_creation_tokens / 1_000_000) * pricing.cache_write_price
    cache_read_cost = (cache_read_tokens / 1_000_000) * pricing.cache_read_price

    return input_cost + output_cost + cache_write_cost + cache_read_cost


def format_cost(cost: float) -> str:
    """
    Format cost value for display.

    Args:
        cost: Cost in USD

    Returns:
        Formatted string (e.g., "$1.23", "$0.05", "$123.45")
    """
    if cost < 0.01:
        return f"${cost:.4f}"  # Show more precision for very small amounts
    elif cost < 1.0:
        return f"${cost:.3f}"
    else:
        return f"${cost:.2f}"


#endregion
