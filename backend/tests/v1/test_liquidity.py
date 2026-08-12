"""D2: liquidation cost and the position limit."""

from __future__ import annotations

import pytest

from risk_engine.v1 import hedging, liquidity


def test_cost_increases_with_size(private_state, params):
    depth = hedging.effective_depth(private_state)
    previous = -1.0
    for notional in (10_000.0, 100_000.0, 500_000.0, 2_000_000.0):
        cost = liquidity.liquidation_cost(notional, private_state, depth, params)
        assert cost > previous
        previous = cost


def test_cost_is_convex_when_impact_is_superlinear(private_state, params):
    """Fitted alpha exceeds 1 on illiquid profiles, so doubling size more than
    doubles the impact component."""
    depth = hedging.effective_depth(private_state)
    single = liquidity.impact_cost(500_000.0, private_state, depth)
    double = liquidity.impact_cost(1_000_000.0, private_state, depth)
    assert double > 2 * single


def test_cost_decreases_with_depth(private_state, params):
    previous = float("inf")
    for depth in (100_000.0, 500_000.0, 5_000_000.0):
        cost = liquidity.liquidation_cost(500_000.0, private_state, depth, params)
        assert cost < previous
        previous = cost


def test_unwind_horizon_is_size_over_participation_times_depth(private_state, params):
    depth = 1_000_000.0
    assert liquidity.unwind_days(400_000.0, depth, params) == pytest.approx(
        400_000.0 / (params.participation_rate * depth)
    )


def test_position_limit_is_linear_in_effective_depth(private_state, params):
    single = liquidity.position_limit(500_000.0, params)
    double = liquidity.position_limit(1_000_000.0, params)
    assert double == pytest.approx(2 * single)


def test_position_limit_unwinds_within_the_policy_horizon(private_state, params):
    """The limit is defined by the horizon, so the horizon must come back out."""
    depth = hedging.effective_depth(private_state)
    limit = liquidity.position_limit(depth, params)
    assert liquidity.unwind_days(limit, depth, params) == pytest.approx(params.max_unwind_days)


def test_timing_cost_uses_average_inventory(private_state, params):
    """A linear trajectory carries a third of the variance of holding throughout."""
    depth = hedging.effective_depth(private_state)
    notional = liquidity.position_limit(depth, params)
    tau_u = liquidity.unwind_days(notional, depth, params)

    import math

    from risk_engine.v1 import units

    naive = params.z_maintenance * private_state.volatility * math.sqrt(units.years(tau_u))
    actual = liquidity.timing_cost(notional, private_state, depth, params)
    assert actual == pytest.approx(naive / math.sqrt(3.0))


def test_liquidity_and_hedgeability_compound(private_state, params):
    """The interaction is not imposed; it comes from convexity in depth.

    Halving spot depth and removing the hedge should cost more than the sum of
    doing each alone.
    """
    notional = 300_000.0

    def cost(state):
        return liquidity.liquidation_cost(
            notional, state, hedging.effective_depth(state), params
        )

    base = cost(private_state)
    thin = cost(private_state.model_copy(update={"spot_depth": private_state.spot_depth / 2}))
    unhedged = cost(private_state.model_copy(update={"hedge_depth": 0.0}))
    both = cost(
        private_state.model_copy(
            update={"spot_depth": private_state.spot_depth / 2, "hedge_depth": 0.0}
        )
    )

    assert both - base > (thin - base) + (unhedged - base)
