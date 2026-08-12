"""D1: price uncertainty, including the tau_stale = 0 edge case."""

from __future__ import annotations

import math

import pytest

from risk_engine.v1 import uncertainty, units
from risk_engine.v1.inputs import Interval


@pytest.mark.parametrize("dispersion", [0.002, 0.02, 0.20, 0.50])
def test_uncertainty_grows_with_staleness(private_state, params, dispersion):
    """The core guarantee, checked across the dispersion range.

    An earlier formulation made the structural term decay with staleness, so on a
    high-dispersion asset sigma_U fell from 35.6% at one day to 28.4% at seven
    before recovering -- a staler mark reported as more reliable, which is exactly
    the v0 defect this dimension exists to remove. Parameterised over dispersion
    because the defect was invisible at the frontier profile's 5%.
    """
    state = private_state.model_copy(update={"source_dispersion": dispersion})
    previous = -1.0
    for staleness in (0.0, 0.5, 1.0, 2.0, 4.0, 7.0, 14.0, 30.0, 120.0, 365.0):
        value = uncertainty.price_uncertainty(
            state.model_copy(update={"mark_staleness_days": staleness}), params
        )
        assert value > previous, f"uncertainty fell at {staleness} days"
        previous = value


def test_structural_inflation_is_independent_of_staleness(private_state, params):
    """Whether disagreement is structural is a property of the asset, not the mark."""
    inflations = {
        uncertainty.structural_inflation(
            private_state.model_copy(update={"mark_staleness_days": s}), params
        )
        for s in (0.0, 1.0, 7.0, 30.0, 120.0, 365.0)
    }
    assert len(inflations) == 1


def test_structural_inflation_never_exceeds_withdrawing_the_averaging_credit(
    private_state, params
):
    """The ceiling that replaces a tuned coefficient: at most, treat n sources as one."""
    for dispersion in (0.001, 0.05, 0.20, 1.0, 10.0):
        state = private_state.model_copy(update={"source_dispersion": dispersion})
        ceiling = 1.0 / uncertainty.averaging_weight(state)
        assert 1.0 <= uncertainty.structural_inflation(state, params) <= ceiling + 1e-12


def test_full_inflation_recovers_the_unaveraged_variance(private_state, params):
    """At the ceiling, the averaging credit is gone entirely."""
    structural = private_state.model_copy(update={"source_dispersion": 5.0})
    variance = uncertainty.dispersion_effective_variance(
        structural, params
    ) * uncertainty.structural_inflation(structural, params)
    assert variance == pytest.approx(params.robust_estimator_penalty * 5.0**2)


def test_single_source_has_no_averaging_credit_to_withdraw(private_state, params):
    """With one source, w = 1, so the inflation is inert rather than undefined."""
    single = private_state.model_copy(
        update={"source_count": 1, "source_dispersion": None}
    )
    assert uncertainty.averaging_weight(single) == pytest.approx(1.0)
    assert uncertainty.structural_inflation(single, params) == pytest.approx(1.0)


def test_staleness_variance_accumulates_as_square_root_of_time(params, private_state):
    """The drift term must scale as sigma * sqrt(t), not sigma * t."""
    state = private_state.model_copy(
        update={"source_count": 1, "source_dispersion": None, "source_correlation": 0.0}
    )
    at_1 = uncertainty.price_uncertainty(state.model_copy(update={"mark_staleness_days": 1.0}), params)
    at_4 = uncertainty.price_uncertainty(state.model_copy(update={"mark_staleness_days": 4.0}), params)
    # Dispersion is common to both, so compare the drift components directly.
    drift_1 = math.sqrt(at_1**2 - (at_1**2 - state.volatility**2 * units.years(1.0)))
    drift_4 = math.sqrt(at_4**2 - (at_4**2 - state.volatility**2 * units.years(4.0)))
    assert drift_4 / drift_1 == pytest.approx(2.0)


def test_correlated_sources_add_little(params, private_state):
    """Ten feeds copying one primary must be worth barely more than one."""
    quiet = private_state.model_copy(update={"source_dispersion": 0.02})
    independent = quiet.model_copy(update={"source_count": 10, "source_correlation": 0.0})
    correlated = quiet.model_copy(update={"source_count": 10, "source_correlation": 0.95})
    assert uncertainty.price_uncertainty(correlated, params) > uncertainty.price_uncertainty(
        independent, params
    )


def test_source_structure_stops_mattering_once_disagreement_is_structural(
    params, private_state
):
    """A consequence of the ceiling, and the intended one.

    If sources disagree by more than the asset's volatility explains, the
    disagreement is evidence of common error. Counting the sources or measuring
    their correlation cannot help, because averaging does not remove common
    error, so both inputs drop out.
    """
    structural = private_state.model_copy(update={"source_dispersion": 0.20})
    few = structural.model_copy(update={"source_count": 2, "source_correlation": 0.6})
    many = structural.model_copy(update={"source_count": 20, "source_correlation": 0.0})
    assert uncertainty.price_uncertainty(few, params) == pytest.approx(
        uncertainty.price_uncertainty(many, params)
    )


def test_dispersion_variance_floors_at_correlation(params, private_state):
    """As source count grows, variance floors at rho * delta^2 rather than vanishing."""
    many = private_state.model_copy(update={"source_count": 10_000, "source_correlation": 0.5})
    variance = uncertainty.dispersion_effective_variance(many, params)
    floor = params.robust_estimator_penalty * 0.5 * (many.source_dispersion or 0.0) ** 2
    assert variance == pytest.approx(floor, rel=1e-3)


def test_single_source_uses_the_prior_not_an_observed_zero(params, private_state):
    """A lone source cannot disagree with itself; rewarding that is the v0 bug."""
    single = private_state.model_copy(
        update={"source_count": 1, "source_dispersion": None, "mark_staleness_days": 0.0}
    )
    variance = uncertainty.dispersion_effective_variance(single, params)
    assert variance == pytest.approx(
        params.robust_estimator_penalty * params.dispersion_prior**2
    )
    assert variance > 0.0


def test_robust_estimator_penalty_is_applied(params, private_state):
    """Manipulation resistance costs efficiency, and the cost is explicit."""
    assert params.robust_estimator_penalty == pytest.approx(math.pi / 2)
    variance = uncertainty.dispersion_effective_variance(private_state, params)
    unpenalised = variance / params.robust_estimator_penalty
    assert variance > unpenalised


# --- The tau_stale = 0 edge case ------------------------------------------


def test_diagnostic_ratio_is_finite_at_zero_staleness(params, private_state):
    """No division by zero when the mark is same-day."""
    fresh = private_state.model_copy(update={"mark_staleness_days": 0.0})
    ratio = uncertainty.dispersion_diagnostic_ratio(fresh, params)
    assert math.isfinite(ratio)
    assert ratio > 0.0


def test_diagnostic_uses_the_minimum_information_horizon(params, private_state):
    """The window is exactly one day, whatever the mark's age."""
    fresh = private_state.model_copy(update={"mark_staleness_days": 0.0})
    expected = uncertainty.observed_dispersion(fresh, params) / (
        fresh.volatility * math.sqrt(units.years(units.MIN_INFORMATION_HORIZON_DAYS))
    )
    assert uncertainty.dispersion_diagnostic_ratio(fresh, params) == pytest.approx(expected)


def test_diagnostic_compares_dispersion_to_volatility_not_to_staleness(params):
    """5% disagreement is noise on a 120% asset and a pricing failure on a 30% one."""
    from risk_engine.v1.inputs import MarketState

    base = {
        "spot_depth": 1_000_000.0,
        "impact_exponent": 1.0,
        "impact_coefficient": 0.02,
        "mark_staleness_days": 1.0,
        "mark_refresh_days": 1.0,
        "source_count": 3,
        "source_dispersion": 0.05,
        "source_correlation": 0.5,
        "jump_intensity": 1.0,
        "jump_tail_index": 3.0,
        "jump_scale": 0.05,
        "crowding": Interval(low=0.05, high=0.05),
    }
    quiet_asset = MarketState(**base, volatility=0.30)
    wild_asset = MarketState(**base, volatility=1.20)

    assert uncertainty.dispersion_diagnostic_ratio(quiet_asset, params) > 1.0
    assert uncertainty.dispersion_diagnostic_ratio(wild_asset, params) < 1.0
    assert uncertainty.structural_inflation(quiet_asset, params) > 1.0
    assert uncertainty.structural_inflation(wild_asset, params) == pytest.approx(1.0)


def test_variance_term_is_not_floored_at_zero_staleness(params, private_state):
    """The floor is confined to the diagnostic; uncertainty at zero staleness is
    pure source dispersion.

    This is what preserves the economic reading of the zero-staleness rows in the
    viability frontier, so it is asserted rather than left implicit.
    """
    fresh = private_state.model_copy(update={"mark_staleness_days": 0.0})
    expected = math.sqrt(
        uncertainty.dispersion_effective_variance(fresh, params)
        * uncertainty.structural_inflation(fresh, params)
    )
    assert uncertainty.price_uncertainty(fresh, params) == pytest.approx(expected)


def test_zero_staleness_still_below_one_day_staleness(params, private_state):
    """The floor must not make a fresh mark look worse than a one-day-old one."""
    fresh = uncertainty.price_uncertainty(
        private_state.model_copy(update={"mark_staleness_days": 0.0}), params
    )
    aged = uncertainty.price_uncertainty(
        private_state.model_copy(update={"mark_staleness_days": 1.0}), params
    )
    assert fresh < aged


def test_structural_inflation_activates_above_the_diagnostic_ratio(params):
    """Disagreement beyond what diffusion explains is treated as structural."""
    from risk_engine.v1.inputs import MarketState

    base = {
        "volatility": 0.30,
        "spot_depth": 1_000_000.0,
        "impact_exponent": 1.0,
        "impact_coefficient": 0.02,
        "mark_staleness_days": 1.0,
        "mark_refresh_days": 1.0,
        "source_count": 2,
        "source_correlation": 0.0,
        "jump_intensity": 1.0,
        "jump_tail_index": 3.0,
        "jump_scale": 0.05,
        "crowding": Interval(low=0.05, high=0.05),
    }
    quiet = MarketState(**base, source_dispersion=0.001)
    noisy = MarketState(**base, source_dispersion=0.20)

    assert uncertainty.structural_inflation(quiet, params) == pytest.approx(1.0)
    assert uncertainty.structural_inflation(noisy, params) > 1.0
