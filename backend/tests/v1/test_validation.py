"""End-to-end validation targets from the v1 specification.

These are the checks that would catch a wrong model rather than a wrong line of
code: dimensional invariance, whether the jump quantile hits its stated
tolerance, whether the regime switches fire in the right order, and whether the
viability frontier reproduces.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from risk_engine.v1 import (
    Interval,
    MarketState,
    cascade,
    evaluate_risk_v1,
    hedging,
    jumps,
    liquidity,
    units,
)
from risk_engine.v1.regimes import Mechanism, RegimeId
from simulations.viability_frontier import first_trip, state_at

# --------------------------------------------------------------------------
# Dimensional invariance
# --------------------------------------------------------------------------


def test_scaling_every_notional_leaves_fractions_unchanged(private_state, params):
    """Margins are fractions of notional and must not depend on currency scale."""
    scale = 1_000.0
    scaled = private_state.model_copy(
        update={
            "spot_depth": private_state.spot_depth * scale,
            "hedge_depth": private_state.hedge_depth * scale,
            "open_interest_long": private_state.open_interest_long * scale,
            "open_interest_short": private_state.open_interest_short * scale,
        }
    )
    base = evaluate_risk_v1(private_state, params)
    grown = evaluate_risk_v1(scaled, params)

    assert grown.margin_diagnostics.required_initial_margin == pytest.approx(
        base.margin_diagnostics.required_initial_margin
    )
    assert grown.margin_diagnostics.required_maintenance_margin == pytest.approx(
        base.margin_diagnostics.required_maintenance_margin
    )
    assert grown.dimensions.unwind_days_at_limit == pytest.approx(
        base.dimensions.unwind_days_at_limit
    )


def test_scaling_every_notional_scales_size_limits(private_state, params):
    scale = 1_000.0
    scaled = private_state.model_copy(
        update={
            "spot_depth": private_state.spot_depth * scale,
            "hedge_depth": private_state.hedge_depth * scale,
        }
    )
    base = evaluate_risk_v1(private_state, params)
    grown = evaluate_risk_v1(scaled, params)

    assert grown.size_limits.position_limit == pytest.approx(
        base.size_limits.position_limit * scale
    )
    assert grown.size_limits.open_interest_cap_low == pytest.approx(
        base.size_limits.open_interest_cap_low * scale
    )


def test_unwind_horizon_is_a_time_not_a_ratio(private_state, params):
    """Depth is USD/day, so notional over depth must come out in days.

    Doubling depth halves the time to exit a fixed position. Under v0's reading of
    depth as a stock this quantity had no units at all.
    """
    fast = liquidity.unwind_days(1_000_000.0, 1_000_000.0, params)
    slow = liquidity.unwind_days(1_000_000.0, 500_000.0, params)
    assert slow == pytest.approx(2 * fast)
    assert fast == pytest.approx(1.0 / params.participation_rate)


def test_annualised_inputs_are_converted_before_use(params):
    """The v0 defect: mixing annualised rates with day-valued horizons.

    At 120 days, treating tau as years overstates uncertainty by roughly 19x. The
    correct value is sigma * sqrt(120/365).
    """
    state = _frontier_state(volatility=0.90, staleness=120.0, dispersion=1e-9)
    sigma_u = evaluate_risk_v1(state, params).dimensions.price_uncertainty
    assert sigma_u == pytest.approx(0.90 * math.sqrt(120.0 / 365.0), rel=1e-3)
    assert sigma_u < 1.0


# --------------------------------------------------------------------------
# Jump-risk target
# --------------------------------------------------------------------------


def test_jump_quantile_hits_its_stated_tolerance(private_state, params):
    """Monte Carlo: gaps beyond the margined level occur at about eps_jump.

    Compound Poisson arrivals with Pareto log jump sizes, which is the process the
    analytic quantile inverts.
    """
    horizon_days = 30.0
    rng = np.random.default_rng(20260811)
    paths = 200_000

    state = private_state
    threshold = jumps.jump_log_quantile(state, horizon_days, params)
    assert jumps.jump_constraint_binds(state, horizon_days, params)

    intensity = state.jump_intensity * units.years(horizon_days)
    counts = rng.poisson(intensity, size=paths)
    total = counts.sum()
    sizes = state.jump_scale * (1.0 - rng.random(total)) ** (-1.0 / state.jump_tail_index)

    exceeded = np.zeros(paths, dtype=bool)
    offsets = np.concatenate([[0], np.cumsum(counts)])
    largest = np.maximum.reduceat(
        np.concatenate([sizes, [0.0]]), offsets[:-1].clip(max=total)
    )
    exceeded = np.where(counts > 0, largest > threshold, False)

    realised = exceeded.mean()
    assert realised == pytest.approx(params.jump_tolerance, rel=0.20), (
        f"realised exceedance {realised:.4%} against target {params.jump_tolerance:.2%}"
    )


def test_jump_loss_is_the_quantile_in_return_space(private_state, params):
    """Log-space quantile converted once, respecting limited liability."""
    quantile = jumps.jump_log_quantile(private_state, 30.0, params)
    assert jumps.jump_loss(private_state, 30.0, params) == pytest.approx(
        1.0 - math.exp(-quantile)
    )


# --------------------------------------------------------------------------
# Oracle staleness and regime switching
# --------------------------------------------------------------------------


def _frontier_state(volatility: float, staleness: float, dispersion: float = 0.05):
    return MarketState(
        volatility=volatility,
        spot_depth=350_000.0,
        impact_exponent=1.15,
        impact_coefficient=0.0703,
        hedge_depth=17_500.0,
        hedge_volatility=0.60,
        hedge_correlation=0.22,
        hedge_ratio=0.05,
        mark_staleness_days=staleness,
        mark_refresh_days=max(staleness, 1.0),
        source_count=3,
        source_dispersion=dispersion,
        source_correlation=0.5,
        jump_intensity=10.0,
        jump_tail_index=2.0,
        jump_scale=0.05,
        open_interest_long=5_000_000.0,
        open_interest_short=500_000.0,
        crowding=Interval(low=0.02, high=0.20),
    )


def test_staleness_degrades_the_mechanism_monotonically(params):
    """Viability, once lost, is never regained by ageing the mark further."""
    seen_failure = False
    for staleness in (0.0, 1.0, 3.0, 7.0, 14.0, 30.0, 90.0, 365.0):
        outputs = evaluate_risk_v1(_frontier_state(0.90, staleness), params)
        if seen_failure:
            assert not outputs.viable_as_continuous_perp, (
                f"viability recovered at {staleness} days"
            )
        seen_failure = seen_failure or not outputs.viable_as_continuous_perp
    assert seen_failure


def test_margin_increases_monotonically_with_staleness(params):
    previous = -1.0
    for staleness in (0.0, 1.0, 7.0, 30.0, 120.0, 365.0):
        margin = evaluate_risk_v1(
            _frontier_state(0.90, staleness), params
        ).margin_diagnostics.required_initial_margin
        assert margin > previous
        previous = margin


def test_r2_fires_once_the_mark_outlasts_an_unwind(params):
    """At the position limit the unwind horizon is the policy maximum, so R2
    reduces to a comparison between refresh cadence and that horizon."""
    below = evaluate_risk_v1(_frontier_state(0.90, 3.0), params)
    above = evaluate_risk_v1(_frontier_state(0.90, 30.0), params)
    assert RegimeId.R2 not in {t.id for t in below.triggered_regimes}
    assert RegimeId.R2 in {t.id for t in above.triggered_regimes}


def test_r1_arrives_sooner_for_more_volatile_assets(params):
    """Higher volatility exhausts the collateral budget at less staleness."""
    days = [first_trip(RegimeId.R1, sigma) for sigma in (0.30, 0.50, 0.80, 1.00, 1.20)]
    assert all(day is not None for day in days)
    assert days == sorted(days, reverse=True)


def test_low_volatility_trips_the_signal_to_noise_condition_immediately(params):
    """5% disagreement is noise on a 120% asset and a pricing failure on a 30% one."""
    quiet = evaluate_risk_v1(_frontier_state(0.30, 0.0), params)
    assert RegimeId.R3 in {t.id for t in quiet.triggered_regimes}


# --------------------------------------------------------------------------
# Cascade stability
# --------------------------------------------------------------------------


def test_cap_sits_exactly_on_the_stability_ceiling(private_state, params):
    depth = hedging.effective_depth(private_state)
    for phi in (0.02, 0.05, 0.20):
        cap = cascade.open_interest_cap(depth, private_state, phi, params)
        assert cascade.amplification(cap, depth, private_state, phi) == pytest.approx(
            params.cascade_ceiling
        )


def test_beyond_the_cap_amplification_exceeds_the_ceiling(private_state, params):
    depth = hedging.effective_depth(private_state)
    cap = cascade.open_interest_cap(depth, private_state, 0.05, params)
    assert cascade.amplification(1.5 * cap, depth, private_state, 0.05) > params.cascade_ceiling


def test_total_amplification_stays_finite_at_the_cap(private_state, params):
    """1 / (1 - beta): convergent, and at most a doubling under the default ceiling."""
    depth = hedging.effective_depth(private_state)
    cap = cascade.open_interest_cap(depth, private_state, 0.05, params)
    beta = cascade.amplification(cap, depth, private_state, 0.05)
    assert 1.0 / (1.0 - beta) == pytest.approx(2.0)


def test_reported_beta_at_cap_equals_the_ceiling(private_state, params):
    outputs = evaluate_risk_v1(private_state, params)
    assert outputs.dimensions.cascade_beta_at_cap == pytest.approx(params.cascade_ceiling)


# --------------------------------------------------------------------------
# phi_1 sensitivity
# --------------------------------------------------------------------------


def test_cap_range_spans_an_order_of_magnitude_over_the_assumed_interval(
    private_state, params
):
    """L5: phi_1 is unobservable here, and the resulting spread is the finding.

    A 10x range in the assumption moves the cap by roughly 10x, which is why a
    point estimate would be the most misleading number the engine could print.
    """
    outputs = evaluate_risk_v1(private_state, params)
    spread = outputs.size_limits.open_interest_cap_high / outputs.size_limits.open_interest_cap_low
    assumed_spread = private_state.crowding.high / private_state.crowding.low
    assert spread == pytest.approx(assumed_spread, rel=0.05)
    assert spread > 5.0


def test_point_crowding_is_required_before_a_point_cap_is_published(
    private_state, params
):
    interval = evaluate_risk_v1(private_state, params)
    point = evaluate_risk_v1(
        private_state.model_copy(update={"crowding": Interval.point(0.05)}), params
    )
    assert interval.size_limits.open_interest_cap_point is None
    assert point.size_limits.open_interest_cap_point is not None


def test_crowding_does_not_affect_margin(private_state, params):
    """Cascade risk is a size limit, not a collateral requirement."""
    tight = evaluate_risk_v1(
        private_state.model_copy(update={"crowding": Interval.point(0.02)}), params
    )
    crowded = evaluate_risk_v1(
        private_state.model_copy(update={"crowding": Interval.point(0.20)}), params
    )
    assert tight.margin_diagnostics.required_initial_margin == pytest.approx(
        crowded.margin_diagnostics.required_initial_margin
    )


# --------------------------------------------------------------------------
# Viability frontier
# --------------------------------------------------------------------------


def test_price_uncertainty_reproduces_the_specification_table(params):
    """sigma_U from the headline table, reproduced exactly."""
    expected = {0.0: 0.052, 1.0: 0.070, 7.0: 0.135, 14.0: 0.184, 30.0: 0.263, 120.0: 0.519}
    for staleness, target in expected.items():
        sigma_u = evaluate_risk_v1(
            state_at(0.90, staleness), params
        ).dimensions.price_uncertainty
        assert sigma_u == pytest.approx(target, abs=0.001)


def test_headline_profile_is_viable_only_while_freshly_marked(params):
    assert evaluate_risk_v1(state_at(0.90, 0.0), params).viable_as_continuous_perp
    assert evaluate_risk_v1(state_at(0.90, 1.0), params).viable_as_continuous_perp
    assert not evaluate_risk_v1(state_at(0.90, 7.0), params).viable_as_continuous_perp


def test_frontier_ends_in_a_settled_instrument_not_a_worse_perp(params):
    outputs = evaluate_risk_v1(state_at(0.90, 120.0), params)
    assert outputs.recommended_mechanism is Mechanism.SETTLED_FORWARD
    assert outputs.tradable is None
    assert outputs.margin_diagnostics.required_initial_margin > 2.0


def test_every_precondition_eventually_fails(params):
    """All three are reachable; none is algebraically dead."""
    triggered = {t.id for t in evaluate_risk_v1(state_at(0.90, 120.0), params).triggered_regimes}
    assert triggered == {RegimeId.R1, RegimeId.R2, RegimeId.R3}
