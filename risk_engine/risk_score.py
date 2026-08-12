"""Composite risk score.

Reduces the full input vector to a single 0-100 number plus a breakdown of what
drove it. Everything downstream (margin, leverage, limits) is a function of this
score, which keeps the engine's behaviour monotonic and easy to reason about:
a market cannot become riskier on every axis and still receive looser limits.
"""

from __future__ import annotations

from .inputs import RiskInputs
from .oracle import oracle_penalty

# Weights must sum to 1.0. These are judgement calls, not calibrated estimates.
COMPONENT_WEIGHTS: dict[str, float] = {
    "illiquidity": 0.25,
    "price_discovery": 0.20,
    "jump_risk": 0.20,
    "unhedgeability": 0.15,
    "event_proximity": 0.10,
    "crowding": 0.10,
}

# Open interest at this multiple of market depth is treated as fully crowded.
CROWDING_DEPTH_MULTIPLE = 5.0


def crowding_penalty(inputs: RiskInputs) -> float:
    """Penalise open interest that is large relative to hedging depth.

    Identical parameters are not equally safe at different sizes: a position the
    venue can unwind into available depth is a different risk than one that must
    move the market to close. Returns 1.0 when open interest reaches
    ``CROWDING_DEPTH_MULTIPLE`` times depth, and 1.0 whenever depth is zero.
    """
    if inputs.market_depth <= 0.0:
        return 1.0
    ratio = inputs.current_open_interest / (inputs.market_depth * CROWDING_DEPTH_MULTIPLE)
    return min(ratio, 1.0)


def score_components(inputs: RiskInputs) -> dict[str, float]:
    """Return each unweighted risk component in [0, 1], where 1 is worst."""
    return {
        "illiquidity": 1.0 - inputs.liquidity_score,
        "price_discovery": oracle_penalty(inputs),
        "jump_risk": inputs.jump_risk,
        "unhedgeability": 1.0 - inputs.hedgeability_score,
        "event_proximity": inputs.event_proximity,
        "crowding": crowding_penalty(inputs),
    }


def score_breakdown(inputs: RiskInputs) -> dict[str, float]:
    """Return each component's weighted contribution to the 0-100 score."""
    components = score_components(inputs)
    return {name: 100.0 * COMPONENT_WEIGHTS[name] * value for name, value in components.items()}


def compute_risk_score(inputs: RiskInputs) -> float:
    """Return the composite risk score in [0, 100].

    Placeholder implementation: a weighted linear blend of the components.

    Future work: the linear form assumes risks are substitutable, which is the
    weakest assumption in the engine. In practice illiquidity and unhedgeability
    interact multiplicatively -- an asset you cannot price *and* cannot hedge is
    far worse than the sum of the two problems.
    """
    return sum(score_breakdown(inputs).values())
