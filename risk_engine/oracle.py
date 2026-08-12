"""Price-discovery quality.

Perp risk parameters are only as good as the mark they are enforced against. A
liquid public asset has a continuously observable price; a private-company
exposure may only reprice on a funding round, so the "current price" is an
estimate with an age and a confidence interval. This module collapses the three
price-discovery inputs (confidence, staleness, dispersion) into a single
reliability number in [0, 1] that the rest of the engine can consume.
"""

from __future__ import annotations

from .inputs import RiskInputs

# Days after which a stale mark retains half of its informational value.
STALENESS_HALF_LIFE_DAYS = 30.0

# Dispersion (as a fraction of price) treated as total disagreement.
DISPERSION_CEILING = 0.25

# Relative importance of each price-discovery dimension. Placeholder weights.
CONFIDENCE_WEIGHT = 0.45
STALENESS_WEIGHT = 0.35
DISPERSION_WEIGHT = 0.20


def staleness_factor(price_staleness_days: float) -> float:
    """Decay the value of a mark as it ages.

    Uses exponential decay with a half-life of ``STALENESS_HALF_LIFE_DAYS``: a
    same-day mark scores 1.0, a 30-day-old mark scores 0.5, a 90-day-old mark
    scores 0.125.

    Future work: replace the fixed half-life with an asset-specific decay
    calibrated to observed repricing frequency, since a quarterly-marked private
    position and a daily-marked ETF should not decay at the same rate.
    """
    return 0.5 ** (max(price_staleness_days, 0.0) / STALENESS_HALF_LIFE_DAYS)


def dispersion_factor(oracle_dispersion: float) -> float:
    """Penalise disagreement between price sources.

    Linear from 1.0 (all sources agree) to 0.0 at ``DISPERSION_CEILING``.

    Future work: dispersion should be interpreted relative to the asset's own
    volatility. Sources differing by 5% matters far more for a stable asset than
    for a highly volatile one.
    """
    return 1.0 - min(max(oracle_dispersion, 0.0) / DISPERSION_CEILING, 1.0)


def oracle_reliability(inputs: RiskInputs) -> float:
    """Return overall confidence in the reference price, in [0, 1].

    Placeholder implementation: a weighted average of stated confidence, mark
    freshness, and source agreement. A weighted average is used because it is
    easy to explain and to audit; a multiplicative form would be more punitive
    when any single dimension collapses, which is likely the better long-run
    choice and is tracked in ``docs/assumptions.md``.
    """
    return (
        CONFIDENCE_WEIGHT * inputs.oracle_confidence
        + STALENESS_WEIGHT * staleness_factor(inputs.price_staleness_days)
        + DISPERSION_WEIGHT * dispersion_factor(inputs.oracle_dispersion)
    )


def oracle_penalty(inputs: RiskInputs) -> float:
    """Return the price-discovery penalty, in [0, 1], where 1 is worst."""
    return 1.0 - oracle_reliability(inputs)
