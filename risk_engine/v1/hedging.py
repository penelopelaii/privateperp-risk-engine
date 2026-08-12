"""D4: hedgeability as a modifier, never as a penalty term.

Hedgeability does not get its own additive slot in a risk score. It acts through
two channels -- residual volatility and effective depth -- and because
liquidation cost is convex in position-over-depth, the interaction between poor
liquidity and poor hedgeability emerges from that convexity instead of being
imposed by a hand-tuned cross term.
"""

from __future__ import annotations

import math

from .inputs import MarketState


def hedge_effectiveness(state: MarketState) -> float:
    """rho_h^2: the R-squared of the hedge regression, in [0, 1].

    v0's ``theta = 1 - sigma_basis^2 / sigma^2`` reached -5.25 for a hedge more
    volatile than the underlying, which fed through to an effective depth *below*
    spot depth -- implying that access to a bad hedge makes an asset harder to
    exit. Parameterising by correlation instead makes the quantity bounded by
    construction, with no clamping required.
    """
    if state.hedge_depth <= 0.0 or state.hedge_correlation is None:
        return 0.0
    return state.hedge_correlation**2


def residual_volatility(state: MarketState) -> float:
    """Volatility remaining after hedging a fraction H at the min-variance ratio.

    ``sigma^2 * [1 - rho^2 * (2H - H^2)]``, which lies in
    ``[sigma^2 (1 - rho^2), sigma^2]`` for every admissible input: it can neither
    exceed the unhedged variance nor go negative.
    """
    rho_squared = hedge_effectiveness(state)
    h = state.hedge_ratio
    return state.volatility * math.sqrt(1.0 - rho_squared * (2.0 * h - h**2))


def effective_depth(state: MarketState, depth_multiplier: float = 1.0) -> float:
    """D_eff: exit capacity per day, combining spot and hedge venues.

    Capacity and variance reduction are different quantities and do not share a
    coefficient. Offsetting one unit of exposure requires ``beta_mv`` units of the
    hedge instrument, while the risk removed scales with ``rho_h^2``; combining
    them collapses to a term linear in ``|rho_h|``.

    The simplified form is evaluated directly rather than as
    ``rho_h^2 * (D_hedge / beta_mv)``, which is 0/0 at zero correlation since
    ``beta_mv = rho_h * sigma / sigma_h`` vanishes with ``rho_h``. The two are
    algebraically identical wherever ``rho_h != 0``, and this one is continuous
    at zero, where it correctly returns spot depth alone: a hedge uncorrelated
    with the underlying contributes no exit capacity.
    """
    spot = state.spot_depth * depth_multiplier
    if state.hedge_depth <= 0.0 or state.hedge_correlation is None:
        return spot

    hedge_volatility = state.hedge_volatility or state.volatility
    contribution = (
        state.hedge_ratio
        * abs(state.hedge_correlation)
        * (hedge_volatility / state.volatility)
        * state.hedge_depth
    )
    return spot + contribution
