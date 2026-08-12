"""Leverage recommendation.

Maximum leverage is the reciprocal of initial margin, subject to a hard venue
cap. It is stated separately because it is the number traders actually see, and
because the cap is a policy decision rather than a mathematical result.
"""

from __future__ import annotations

# Venue-wide ceiling, regardless of how benign the market looks.
MAX_ALLOWED_LEVERAGE = 20.0

# Floor below which a market should not be listed at all rather than offered
# with sub-1x leverage.
MIN_ALLOWED_LEVERAGE = 1.0


def recommended_max_leverage(initial_margin_fraction: float) -> float:
    """Return the maximum leverage multiple permitted for new positions.

    Placeholder implementation: ``1 / initial_margin``, clamped to the venue
    range and rounded to one decimal.

    Future work: leverage should also be tiered by position size, so that the
    first $100k of exposure and the marginal $10m of exposure are not offered
    the same terms in a market with limited depth.
    """
    if initial_margin_fraction <= 0.0:
        return MAX_ALLOWED_LEVERAGE
    raw = 1.0 / initial_margin_fraction
    return round(min(max(raw, MIN_ALLOWED_LEVERAGE), MAX_ALLOWED_LEVERAGE), 1)
