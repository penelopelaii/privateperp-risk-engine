"""D3: discontinuous repricing.

Illiquid underlyings do not drift, they jump: a private company can be flat for a
quarter and reprice 30% on a single funding round. Jump sizes are modelled as a
Pareto tail in **log-return space**, so that the implied loss respects limited
liability -- an unbounded Pareto on simple returns assigns mass below -100%.

The interaction between jumps and leverage cannot be written as a penalty term.
A position at leverage ``l`` is wiped out by a return of ``-1/l``, so the
constraint is an inversion of the tail rather than a scaling of it.
"""

from __future__ import annotations

import math

from . import units
from .inputs import MarketState
from .params import PolicyParameters


def expected_exceedances(state: MarketState, horizon_days: float, params: PolicyParameters):
    """lambda * tau / eps_jump: expected jumps beyond the tail scale, per tolerance."""
    return state.jump_intensity * units.years(horizon_days) / params.jump_tolerance


def jump_constraint_binds(
    state: MarketState, horizon_days: float, params: PolicyParameters
) -> bool:
    """Whether a jump beyond the tail scale is expected within tolerance."""
    return expected_exceedances(state, horizon_days, params) > 1.0


def jump_log_quantile(
    state: MarketState, horizon_days: float, params: PolicyParameters
) -> float:
    """m_J: log-return gap the venue accepts exposure to over ``horizon_days``.

    Clamped at the tail scale ``m0``. Without the clamp the expression is
    evaluated outside the Pareto's domain of validity whenever
    ``lambda * tau < eps_jump``, which produces the perverse result that a
    *fatter* tail permits *more* leverage -- at one jump every two years, a tail
    index of 1.5 allowed 50x against 32.9x for a much thinner index of 4.0.

    Below the clamp the correct statement is that the constraint does not bind:
    no jump exceeding ``m0`` is expected within tolerance over that horizon.
    """
    ratio = max(expected_exceedances(state, horizon_days, params), 1.0)
    return state.jump_scale * ratio ** (1.0 / state.jump_tail_index)


def jump_loss(state: MarketState, horizon_days: float, params: PolicyParameters) -> float:
    """Loss as a fraction of notional, bounded below 1 by limited liability."""
    return 1.0 - math.exp(-jump_log_quantile(state, horizon_days, params))


def has_infinite_mean(state: MarketState) -> bool:
    """Whether the tail index rules out expectation-based measures.

    With ``xi <= 1`` the jump distribution has no finite mean, so expected
    shortfall is undefined and only quantile-based outputs are admissible.
    """
    return state.jump_tail_index <= 1.0
