"""D2: what does it cost to get out?

The Almgren-Chriss trade-off: liquidate fast and pay market impact, or liquidate
slowly and pay volatility while you carry the position. Both terms are fractions
of notional, so they are directly comparable to a margin requirement.

This is where poor liquidity and poor hedgeability compound. Neither is a
penalty; both reduce effective depth, and because cost is convex in days-of-depth
(the fitted exponent exceeds 1 on the illiquid synthetic profiles) degrading them
together is worse than the sum of degrading each.
"""

from __future__ import annotations

import math

from . import units
from .inputs import MarketState
from .params import PolicyParameters

# Average inventory over a linear liquidation trajectory carries 1/3 of the
# variance of holding the full position throughout.
LINEAR_TRAJECTORY_VARIANCE_FACTOR = 3.0


def unwind_days(notional: float, effective_depth: float, params: PolicyParameters) -> float:
    """tau_u: days to liquidate ``notional`` at the permitted participation rate."""
    if effective_depth <= 0.0:
        return math.inf
    return notional / (params.participation_rate * effective_depth)


def impact_cost(notional: float, state: MarketState, effective_depth: float) -> float:
    """Price concession from executing, as a fraction of notional."""
    v = units.days_of_depth(notional, effective_depth)
    return state.impact_coefficient * v**state.impact_exponent


def timing_cost(
    notional: float, state: MarketState, effective_depth: float, params: PolicyParameters
) -> float:
    """Adverse drift while the position is being worked, as a fraction of notional."""
    tau_u = unwind_days(notional, effective_depth, params)
    variance_years = units.years(tau_u) / LINEAR_TRAJECTORY_VARIANCE_FACTOR
    return params.z_maintenance * state.volatility * math.sqrt(variance_years)


def liquidation_cost(
    notional: float, state: MarketState, effective_depth: float, params: PolicyParameters
) -> float:
    """C(q): total expected cost of getting flat, as a fraction of notional."""
    return impact_cost(notional, state, effective_depth) + timing_cost(
        notional, state, effective_depth, params
    )


def position_limit(effective_depth: float, params: PolicyParameters) -> float:
    """q_max: the largest position the venue is willing to have to unwind.

    Set by the maximum tolerable unwind horizon, not by a margin-coverage
    condition. The seemingly more elegant "largest position whose liquidation
    cost is covered by its own margin" is circular, because maintenance margin is
    itself defined as that cost plus other terms; numerically it also permits
    positions one to two orders of magnitude larger, since an illiquid asset's
    large margin becomes a large budget for the cost it was sized to cover.
    """
    return params.participation_rate * effective_depth * params.max_unwind_days
