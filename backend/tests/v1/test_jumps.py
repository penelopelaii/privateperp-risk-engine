"""D3: jump risk, tail-index monotonicity, and limited liability."""

from __future__ import annotations

import pytest

from risk_engine.v1 import jumps


def test_jump_loss_respects_limited_liability(private_state, params):
    """A long position cannot lose more than its notional, whatever the tail.

    The log-space parameterisation is what guarantees this; a Pareto on simple
    returns would assign mass below -100%. At absurd parameters the exponential
    underflows to exactly 1.0 in floating point, so the bound is inclusive.
    """
    extreme = private_state.model_copy(
        update={"jump_intensity": 500.0, "jump_tail_index": 1.1, "jump_scale": 0.5}
    )
    assert 0.0 <= jumps.jump_loss(extreme, 365.0, params) <= 1.0


def test_jump_loss_stays_strictly_below_notional_at_plausible_parameters(
    private_state, params
):
    severe = private_state.model_copy(
        update={"jump_intensity": 20.0, "jump_tail_index": 1.5, "jump_scale": 0.15}
    )
    assert jumps.jump_loss(severe, 365.0, params) < 1.0


def test_jump_loss_increases_with_intensity(private_state, params):
    previous = -1.0
    for intensity in (0.5, 2.0, 6.0, 12.0, 50.0):
        loss = jumps.jump_loss(
            private_state.model_copy(update={"jump_intensity": intensity}), 30.0, params
        )
        assert loss >= previous
        previous = loss


def test_jump_loss_increases_with_horizon(private_state, params):
    previous = -1.0
    for horizon in (1.0, 7.0, 30.0, 365.0):
        loss = jumps.jump_loss(private_state, horizon, params)
        assert loss >= previous
        previous = loss


def test_fatter_tail_never_permits_more_leverage(private_state, params):
    """The defect that motivated the domain clamp.

    Without it, at one jump every two years a tail index of 1.5 permitted 50x
    against 32.9x for a much thinner index of 4.0. Sweeping intensity across the
    clamp boundary is the point: the bug only appeared below it.
    """
    for intensity in (0.1, 0.5, 2.0, 6.0, 12.0, 40.0):
        losses = []
        for tail_index in (1.5, 2.5, 4.0):
            state = private_state.model_copy(
                update={"jump_intensity": intensity, "jump_tail_index": tail_index}
            )
            losses.append(jumps.jump_loss(state, 1.0, params))
        # Fatter tail first: loss must be non-increasing as the tail thins.
        assert losses == sorted(losses, reverse=True), (
            f"tail-index monotonicity violated at intensity {intensity}: {losses}"
        )


def test_quantile_is_clamped_at_the_tail_scale(private_state, params):
    """Below the clamp the Pareto is outside its domain of validity."""
    quiet = private_state.model_copy(update={"jump_intensity": 0.01})
    assert jumps.jump_log_quantile(quiet, 1.0, params) == pytest.approx(quiet.jump_scale)


def test_constraint_does_not_bind_when_no_jump_is_expected(private_state, params):
    quiet = private_state.model_copy(update={"jump_intensity": 0.01})
    assert not jumps.jump_constraint_binds(quiet, 1.0, params)


def test_constraint_binds_for_a_jumpy_asset(private_state, params):
    assert jumps.jump_constraint_binds(private_state, 30.0, params)


def test_zero_intensity_gives_the_scale_not_zero(private_state, params):
    """No expected jumps still leaves the tail scale as the exposure."""
    none = private_state.model_copy(update={"jump_intensity": 0.0})
    assert jumps.jump_log_quantile(none, 30.0, params) == pytest.approx(none.jump_scale)


def test_infinite_mean_is_detected(private_state):
    assert jumps.has_infinite_mean(private_state.model_copy(update={"jump_tail_index": 0.9}))
    assert not jumps.has_infinite_mean(private_state.model_copy(update={"jump_tail_index": 2.5}))
