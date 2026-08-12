"""Project v0 inputs onto a v1 market state.

Lets the existing nine-field API reach the v1 engine without changing the API or
the frontend. Every value produced here is an assumption, tagged
``INFERRED_FROM_V0`` so it cannot be mistaken for a measurement.

Two semantic changes deserve emphasis:

* ``market_depth`` is **reinterpreted from a stock to a rate** (USD per day). v0
  only ever forms ratios with it, so its units never surfaced; v1 needs a flow
  because the unwind horizon is a time.
* ``phi_1`` is supplied as an **interval**, so a v0-sourced call can never yield a
  point open interest cap. v0 has no way to know account crowding, and pretending
  otherwise would produce the model's most misleading number.
"""

from __future__ import annotations

import math

from .inputs import RiskInputs
from .v1.inputs import Interval, MarketState
from .v1.provenance import Provenance

# Fitted to data/synthetic/depth_curves.csv (R^2 = 0.84 and 0.98 across five
# hand-written profiles). "Fitted" here means fitted to data this repository
# fabricated: the fit measures internal consistency, not agreement with a market.
IMPACT_EXPONENT_INTERCEPT = 1.184
IMPACT_EXPONENT_SLOPE = -0.440
IMPACT_COEFFICIENT_LOG_INTERCEPT = -2.450
IMPACT_COEFFICIENT_LOG_SLOPE = -2.560

# Pure invention. v0 has no volatility input, and this is the single largest
# assumption in the adapter.
VOLATILITY_BASE = 0.30
VOLATILITY_ILLIQUIDITY_SLOPE = 0.45
VOLATILITY_JUMP_SLOPE = 0.30

# Jump parameters, invented. v0's jump_risk is a 0-1 score with no distributional
# content, so intensity is projected off it and the tail is fixed.
JUMP_INTENSITY_BASE = 0.5
JUMP_INTENSITY_SLOPE = 12.0
JUMP_TAIL_INDEX = 2.5
JUMP_SCALE = 0.05

# v0 cannot observe account crowding, so a deliberately wide interval is used.
CROWDING_INTERVAL = Interval(low=0.02, high=0.20)

# v0's oracle_confidence is a scalar with no source structure behind it.
ASSUMED_SOURCE_COUNT = 3
ASSUMED_SOURCE_CORRELATION = 0.5

ADAPTED_FIELDS = (
    "volatility",
    "spot_depth",
    "impact_exponent",
    "impact_coefficient",
    "hedge_depth",
    "hedge_correlation",
    "hedge_ratio",
    "mark_staleness_days",
    "mark_refresh_days",
    "source_dispersion",
    "jump_intensity",
    "jump_tail_index",
    "jump_scale",
    "crowding",
)


def impact_exponent(liquidity_score: float) -> float:
    return IMPACT_EXPONENT_INTERCEPT + IMPACT_EXPONENT_SLOPE * liquidity_score


def impact_coefficient(liquidity_score: float) -> float:
    return math.exp(
        IMPACT_COEFFICIENT_LOG_INTERCEPT + IMPACT_COEFFICIENT_LOG_SLOPE * liquidity_score
    )


def inferred_volatility(inputs: RiskInputs) -> float:
    """Stand in for the missing volatility input. Not calibrated, not defensible."""
    return (
        VOLATILITY_BASE
        + VOLATILITY_ILLIQUIDITY_SLOPE * (1.0 - inputs.liquidity_score)
        + VOLATILITY_JUMP_SLOPE * inputs.jump_risk
    )


def to_market_state(inputs: RiskInputs) -> MarketState:
    """Build a v1 market state from v0 inputs.

    The mark refresh interval is taken as the observed staleness, floored at one
    day: absent better information, the best estimate of how often a mark arrives
    is how old the current one is.
    """
    liquidity = inputs.liquidity_score
    volatility = inferred_volatility(inputs)

    return MarketState(
        volatility=volatility,
        spot_depth=inputs.market_depth,
        impact_exponent=impact_exponent(liquidity),
        impact_coefficient=impact_coefficient(liquidity),
        hedge_depth=inputs.market_depth * inputs.hedgeability_score,
        hedge_volatility=volatility,
        hedge_correlation=math.sqrt(inputs.hedgeability_score),
        hedge_ratio=inputs.hedgeability_score,
        mark_staleness_days=inputs.price_staleness_days,
        mark_refresh_days=max(inputs.price_staleness_days, 1.0),
        source_count=ASSUMED_SOURCE_COUNT,
        source_dispersion=inputs.oracle_dispersion,
        source_correlation=ASSUMED_SOURCE_CORRELATION,
        jump_intensity=JUMP_INTENSITY_BASE + JUMP_INTENSITY_SLOPE * inputs.jump_risk,
        jump_tail_index=JUMP_TAIL_INDEX,
        jump_scale=JUMP_SCALE,
        open_interest_long=inputs.current_open_interest,
        open_interest_short=0.0,
        crowding=CROWDING_INTERVAL,
    )


def adapter_provenance() -> dict[str, Provenance]:
    """Tag everything the adapter produced.

    The impact parameters are separated out because they are at least fitted to
    something, even if that something is synthetic.
    """
    tags = {field: Provenance.INFERRED_FROM_V0 for field in ADAPTED_FIELDS}
    tags["impact_exponent"] = Provenance.FITTED_SYNTHETIC
    tags["impact_coefficient"] = Provenance.FITTED_SYNTHETIC
    return tags
