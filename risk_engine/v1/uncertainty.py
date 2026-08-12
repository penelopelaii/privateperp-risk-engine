"""D1: how wrong is the mark we enforce against?

The mark is a **robust external reference** -- a trimmed median over independent
external sources -- and never the perp's own order book (specification L1). The
underlying is by construction unhedgeable and un-arbitrageable, so nothing would
anchor the perp book to fundamental value; marking to it would convert price risk
into manipulation risk and then report the result as a *lower* risk number.

Uncertainty is a variance, and variances accumulate rather than average. This is
the module that replaces v0's weighted average of three 0-1 scores, under which a
year-old mark from a confident feed scored better than a same-day undisputed one.
"""

from __future__ import annotations

import math

from . import events, units
from .inputs import MarketState
from .params import PolicyParameters


def observed_dispersion(state: MarketState, params: PolicyParameters) -> float:
    """delta: disagreement between sources.

    With a single source, disagreement is unobservable and a declared prior is
    substituted rather than the observed zero -- otherwise the model rewards
    unverifiability.
    """
    if state.source_count == 1:
        return params.dispersion_prior
    return state.source_dispersion or 0.0


def averaging_weight(state: MarketState) -> float:
    """w: share of dispersion variance that survives averaging the sources.

    ``rho + (1 - rho)/n``. Ten feeds copying one primary are worth barely more
    than one, and at ``rho = 1`` extra sources are worth nothing at all.
    """
    if state.source_count == 1:
        return 1.0
    rho = state.source_correlation
    return rho + (1.0 - rho) / state.source_count


def dispersion_effective_variance(state: MarketState, params: PolicyParameters) -> float:
    """Variance contributed by disagreement between sources.

    Averaging is credited through :func:`averaging_weight`, and robustness is
    charged for: a median is harder to manipulate than a mean and about 57% less
    efficient under normality. L1 accepts that trade deliberately, so the cost
    appears here rather than being ignored.
    """
    base = observed_dispersion(state, params) ** 2 * averaging_weight(state)
    return params.robust_estimator_penalty * base * events.dispersion_multiplier(state.event)


def dispersion_diagnostic_ratio(state: MarketState, params: PolicyParameters) -> float:
    """Ratio of source disagreement to one day's diffusion.

    Above 1, sources disagree by more than the price plausibly moves in a day,
    which points to a structural valuation problem rather than sampling noise.
    The comparison is against **volatility**, not against staleness: 5%
    disagreement is noise on a 120% asset and a pricing failure on a 30% one.

    The window is fixed at ``MIN_INFORMATION_HORIZON_DAYS`` rather than tracking
    ``tau_stale``. Whether disagreement is structural is a property of how the
    asset is priced, not of how old today's mark happens to be. Letting the
    window grow with staleness made the ratio -- and with it the whole term --
    decay as the mark aged, which could report a staler mark as *more* reliable:
    the v0 defect this dimension exists to remove. Fixing the window also makes
    the ratio well defined at ``tau_stale = 0``, where diffusion over the elapsed
    window is zero.
    """
    diffusion = state.volatility * math.sqrt(
        units.years(units.MIN_INFORMATION_HORIZON_DAYS)
    )
    return observed_dispersion(state, params) / diffusion


def structural_inflation(state: MarketState, params: PolicyParameters) -> float:
    """Multiplier on dispersion variance when disagreement looks structural.

    Averaging sources is only justified if their disagreement is independent
    noise. Disagreement larger than the asset's volatility can explain is
    evidence of *common* error instead, and averaging does not remove common
    error. The response is therefore to withdraw the averaging credit rather than
    to apply a free-floating penalty: the multiplier interpolates from 1 up to
    ``1/w``, at which point ``n`` sources are treated as one.

    That ceiling is what removes the need for a tuned coefficient, and it is the
    strongest claim the disagreement alone supports. It is not airtight -- if
    every source errs in the same direction, true uncertainty can exceed even the
    un-averaged spread -- and this term cannot express that case.
    """
    weight = averaging_weight(state)
    blend = min(1.0, max(0.0, dispersion_diagnostic_ratio(state, params) - 1.0))
    return (weight + (1.0 - weight) * blend) / weight


def price_uncertainty(state: MarketState, params: PolicyParameters) -> float:
    """sigma_U: standard deviation of the true price around the mark.

    Monotone increasing in ``tau_stale``: the drift term grows and nothing else
    depends on staleness. The minimum information horizon governs only the
    diagnostic, so the drift term is exactly zero at ``tau_stale = 0`` and
    uncertainty there is pure source dispersion.
    """
    drift_variance = state.volatility**2 * units.years(state.mark_staleness_days)
    dispersion_variance = dispersion_effective_variance(state, params) * structural_inflation(
        state, params
    )
    return math.sqrt(drift_variance + dispersion_variance)
