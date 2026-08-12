"""Margin requirements.

Initial margin answers "how much collateral to open?" and maintenance margin
answers "how little before we liquidate?". The gap between them is the room a
trader has to be wrong before the venue intervenes, and it must widen as the
underlying becomes harder to exit.
"""

from __future__ import annotations

# Initial margin floor, applied to a hypothetical zero-risk market.
BASE_INITIAL_MARGIN = 0.02

# Additional initial margin at maximum risk score.
INITIAL_MARGIN_RANGE = 0.58

# Convexity of the risk-to-margin mapping. >1 keeps liquid markets cheap while
# escalating quickly for genuinely illiquid ones.
INITIAL_MARGIN_CURVATURE = 1.5

# Maintenance margin as a fraction of initial margin: 50% for a benign market,
# tightening toward 75% as risk rises because there is less time to react.
MAINTENANCE_RATIO_BASE = 0.50
MAINTENANCE_RATIO_RANGE = 0.25

MIN_MAINTENANCE_MARGIN = 0.005


def initial_margin(risk_score: float) -> float:
    """Return required initial margin as a fraction of notional.

    Placeholder implementation: a convex curve from ``BASE_INITIAL_MARGIN`` at
    score 0 to ``BASE_INITIAL_MARGIN + INITIAL_MARGIN_RANGE`` at score 100.

    Future work: initial margin should be derived from a target loss quantile
    over the expected liquidation horizon, not from a shaped curve. The horizon
    itself is the interesting variable, since it stretches from seconds on a
    liquid perp to days or weeks on an illiquid underlying.
    """
    normalised = min(max(risk_score, 0.0), 100.0) / 100.0
    return BASE_INITIAL_MARGIN + INITIAL_MARGIN_RANGE * normalised**INITIAL_MARGIN_CURVATURE


def maintenance_margin(risk_score: float) -> float:
    """Return required maintenance margin as a fraction of notional.

    Placeholder implementation: a fraction of initial margin that rises with
    risk, so risky markets have a narrower window between "undercollateralised"
    and "liquidated".

    Future work: the maintenance level should be set so the expected price move
    during an actual unwind is covered, which makes it a function of market
    depth and position size rather than of the score alone.
    """
    normalised = min(max(risk_score, 0.0), 100.0) / 100.0
    ratio = MAINTENANCE_RATIO_BASE + MAINTENANCE_RATIO_RANGE * normalised
    return max(initial_margin(risk_score) * ratio, MIN_MAINTENANCE_MARGIN)
