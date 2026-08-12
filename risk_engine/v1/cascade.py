"""D5: do liquidations feed on themselves?

A price move liquidates accounts, which produces impact, which moves the price
again. The question is whether that loop converges. v0 asked a saturating version
of this question (``min(OI / 5D, 1)``) which was blind above five times depth --
identical parameters at 5x and at 143x depth on the shipped private profile.
Cascade risk is convex and unbounded in position-over-depth, so the transform
must be too.

Uses **directional** open interest: in a downward shock only longs liquidate. Net
open interest governs the venue's residual hedging need, which is a different
question.
"""

from __future__ import annotations

from . import units
from .inputs import Interval, MarketState
from .params import PolicyParameters

REFERENCE_SHOCK = 0.01
"""Initiating price move the cascade is evaluated against, matching phi_1's definition."""


def buffer_cdf(shock: float, phi_1: float) -> float:
    """F_B(x): share of open interest whose buffer is within a move of ``x``.

    Only ``phi_1 = F_B(0.01)`` is observable, so the distribution is closed with
    the minimal assumption available: **linear on the reference interval**. That
    single closure delivers both quantities the cascade needs, consistently --
    ``F_B(x_ref) = phi_1`` exactly, and a constant density ``phi_1 / x_ref``.
    Capped at 1, beyond which everyone has already been liquidated.

    The underlying distribution is a *state variable*, not a parameter: buffers
    depend on entry leverage and on the path since entry, so they cannot be
    recovered from the leverage distribution alone. Collapsing it to one
    interpretable, in-principle-measurable scalar is a deliberate simplification,
    and the resulting sensitivity is reported rather than hidden.
    """
    return min(1.0, phi_1 * shock / REFERENCE_SHOCK)


def buffer_density(phi_1: float) -> float:
    """f_B: density of account buffers near the liquidation trigger, per unit return."""
    return phi_1 / REFERENCE_SHOCK


def amplification_at(
    shock: float,
    open_interest: float,
    effective_depth: float,
    state: MarketState,
    phi_1: float,
) -> float:
    """beta(x): marginal price move per unit of price move, through liquidations.

    A move of ``x`` liquidates ``Q * F_B(x)``, whose impact is
    ``g(l) = gamma * (l / (D_eff * T_ref))^alpha``. Differentiating the fixed
    point ``x = x_0 + g(Q * F_B(x))``:

        beta(x) = alpha * gamma * v^alpha * F_B(x)^(alpha-1) * f_B(x)

    with ``v = Q / (D_eff * T_ref)``. Below 1 the loop converges, with total
    amplification ``1 / (1 - beta)``.
    """
    if open_interest <= 0.0:
        return 0.0
    v = units.days_of_depth(open_interest, effective_depth)
    alpha = state.impact_exponent
    return (
        alpha
        * state.impact_coefficient
        * v**alpha
        * buffer_cdf(shock, phi_1) ** (alpha - 1.0)
        * buffer_density(phi_1)
    )


def amplification(
    open_interest: float, effective_depth: float, state: MarketState, phi_1: float
) -> float:
    """beta at the fixed point of a 1% initiating shock.

    Substituting the linear closure at ``x = x_ref`` collapses the general
    expression to

        beta = (alpha * gamma / x_ref) * (v * phi_1)^alpha

    where ``v * phi_1`` is the notional a 1% move puts up for sale, measured in
    days of depth. That is the quantity cascade risk actually depends on.

    The evaluation point is a choice and is documented as one. For
    ``alpha > 1``, ``beta`` grows with the shock until every account is
    liquidated, so a cap sized here is not conservative against larger shocks;
    the worst case over all shocks is bounded by ``phi_1^(1-alpha)`` times this
    value. For ``alpha < 1``, ``beta`` diverges as the shock vanishes -- concave
    impact has unbounded marginal impact at zero size -- so no shock-independent
    supremum exists and a reference shock is the only well-posed option.
    """
    return amplification_at(REFERENCE_SHOCK, open_interest, effective_depth, state, phi_1)


def open_interest_cap(
    effective_depth: float, state: MarketState, phi_1: float, params: PolicyParameters
) -> float:
    """Q_max: largest directional open interest whose cascade stays within ceiling.

    Inverting :func:`amplification`:

        Q_max = D_eff * T_ref * (beta_max * x_ref / (alpha * gamma))^(1/alpha) / phi_1

    Exactly linear in effective depth, because ``beta`` depends on open interest
    only through the ratio to depth. Exactly inversely proportional to ``phi_1``
    for every ``alpha``, since the two enter only as the product ``v * phi_1``.
    """
    alpha = state.impact_exponent
    v_phi_max = (
        params.cascade_ceiling * REFERENCE_SHOCK / (alpha * state.impact_coefficient)
    ) ** (1.0 / alpha)
    return v_phi_max / phi_1 * effective_depth * units.IMPACT_REFERENCE_PERIOD_DAYS


def open_interest_cap_range(
    effective_depth: float, state: MarketState, params: PolicyParameters
) -> tuple[float, float, float | None]:
    """Return ``(low, high, point)`` over the supplied crowding interval.

    The cap falls as crowding rises, so the low end of the cap corresponds to the
    high end of ``phi_1``. A point value is returned only when the caller supplied
    a point ``phi_1``; otherwise it is ``None``, because publishing a point
    estimate here would be the single most misleading number the engine could
    produce. The elasticity is exactly ``-1``, so the cap's range is the
    assumption's range: a 10x interval in ``phi_1`` is a 10x interval in the cap.
    """
    crowding: Interval = state.crowding
    cap_at_low_crowding = open_interest_cap(effective_depth, state, crowding.low, params)
    cap_at_high_crowding = open_interest_cap(effective_depth, state, crowding.high, params)
    point = cap_at_low_crowding if crowding.is_point else None
    return cap_at_high_crowding, cap_at_low_crowding, point
