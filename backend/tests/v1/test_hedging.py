"""D4: bounded hedge effectiveness, including the rho_h = 0 edge case."""

from __future__ import annotations

import math

import pytest

from risk_engine.v1 import hedging


def test_residual_volatility_never_exceeds_unhedged(private_state):
    """The v0 formulation could imply a hedge that increases risk. This cannot."""
    for correlation in (-1.0, -0.5, 0.0, 0.5, 1.0):
        for ratio in (0.0, 0.25, 0.5, 0.75, 1.0):
            state = private_state.model_copy(
                update={"hedge_correlation": correlation, "hedge_ratio": ratio}
            )
            assert 0.0 <= hedging.residual_volatility(state) <= state.volatility + 1e-12


def test_residual_volatility_hits_the_textbook_bound(private_state):
    """Fully hedged at the min-variance ratio leaves sigma * sqrt(1 - rho^2)."""
    state = private_state.model_copy(update={"hedge_correlation": 0.8, "hedge_ratio": 1.0})
    assert hedging.residual_volatility(state) == pytest.approx(
        state.volatility * math.sqrt(1 - 0.8**2)
    )


def test_unhedged_position_keeps_full_volatility(private_state):
    state = private_state.model_copy(update={"hedge_ratio": 0.0})
    assert hedging.residual_volatility(state) == pytest.approx(state.volatility)


def test_hedge_effectiveness_is_bounded_in_unit_interval(private_state):
    for correlation in (-1.0, -0.3, 0.0, 0.3, 1.0):
        state = private_state.model_copy(update={"hedge_correlation": correlation})
        assert 0.0 <= hedging.hedge_effectiveness(state) <= 1.0


def test_effective_depth_never_falls_below_spot(private_state):
    """Access to a bad hedge must not make an asset harder to exit."""
    for correlation in (-1.0, -0.5, 0.0, 0.5, 1.0):
        for hedge_vol in (0.05, 0.60, 5.0):
            state = private_state.model_copy(
                update={"hedge_correlation": correlation, "hedge_volatility": hedge_vol}
            )
            assert hedging.effective_depth(state) >= state.spot_depth


def test_effective_depth_increases_with_hedge_quality(private_state):
    previous = -1.0
    for correlation in (0.0, 0.25, 0.5, 0.75, 1.0):
        state = private_state.model_copy(update={"hedge_correlation": correlation})
        depth = hedging.effective_depth(state)
        assert depth > previous
        previous = depth


# --- The rho_h = 0 edge case ----------------------------------------------


def test_zero_correlation_is_numerically_safe(private_state):
    """The quotient form is 0/0 here; the simplified form must be finite."""
    state = private_state.model_copy(update={"hedge_correlation": 0.0})
    depth = hedging.effective_depth(state)
    assert math.isfinite(depth)
    assert depth == pytest.approx(state.spot_depth)


def test_effective_depth_is_continuous_at_zero_correlation(private_state):
    """Approaching zero from above must converge to the value at zero."""
    at_zero = hedging.effective_depth(
        private_state.model_copy(update={"hedge_correlation": 0.0})
    )
    near_zero = hedging.effective_depth(
        private_state.model_copy(update={"hedge_correlation": 1e-9})
    )
    assert near_zero == pytest.approx(at_zero, abs=1.0)


def test_simplified_form_matches_the_quotient_form_away_from_zero(private_state):
    """The two are algebraically identical wherever rho_h != 0."""
    state = private_state.model_copy(
        update={"hedge_correlation": 0.6, "hedge_volatility": 0.45, "hedge_ratio": 0.8}
    )
    beta_mv = state.hedge_correlation * state.volatility / state.hedge_volatility
    quotient_form = state.spot_depth + state.hedge_ratio * (
        state.hedge_correlation**2 * (state.hedge_depth / beta_mv)
    )
    assert hedging.effective_depth(state) == pytest.approx(quotient_form)


def test_negative_correlation_still_contributes_capacity(private_state):
    """A short hedge is as good as a long one; only the magnitude matters."""
    positive = hedging.effective_depth(
        private_state.model_copy(update={"hedge_correlation": 0.7})
    )
    negative = hedging.effective_depth(
        private_state.model_copy(update={"hedge_correlation": -0.7})
    )
    assert positive == pytest.approx(negative)


def test_no_hedge_venue_means_spot_depth_only(private_state):
    state = private_state.model_copy(update={"hedge_depth": 0.0})
    assert hedging.effective_depth(state) == pytest.approx(state.spot_depth)
