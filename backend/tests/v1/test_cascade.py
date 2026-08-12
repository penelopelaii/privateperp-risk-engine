"""D5: cascade amplification and the open interest cap."""

from __future__ import annotations

import math

import pytest

from risk_engine.v1 import cascade, hedging
from risk_engine.v1.inputs import Interval


def test_buffer_density_reads_phi_1_as_a_share_per_unit_return():
    assert cascade.buffer_density(0.05) == pytest.approx(5.0)


def test_amplification_is_unbounded_in_open_interest(private_state):
    """v0 saturated at 5x depth. Cascade risk does not."""
    depth = hedging.effective_depth(private_state)
    previous = -1.0
    for multiple in (1, 5, 20, 100, 1000):
        beta = cascade.amplification(multiple * depth, depth, private_state, 0.05)
        assert beta > previous
        previous = beta
    assert previous > 1.0


def test_amplification_is_convex_in_open_interest(private_state):
    """Superlinear impact means the loop tightens faster than linearly."""
    depth = hedging.effective_depth(private_state)
    single = cascade.amplification(depth, depth, private_state, 0.05)
    double = cascade.amplification(2 * depth, depth, private_state, 0.05)
    assert double > 2 * single


def test_cap_is_exactly_linear_in_effective_depth(private_state, params):
    """beta depends on open interest only through the ratio to depth."""
    single = cascade.open_interest_cap(500_000.0, private_state, 0.05, params)
    double = cascade.open_interest_cap(1_000_000.0, private_state, 0.05, params)
    assert double == pytest.approx(2 * single)


def test_cap_achieves_the_ceiling_exactly(private_state, params):
    """Inverting the amplification must land on beta_max."""
    depth = hedging.effective_depth(private_state)
    cap = cascade.open_interest_cap(depth, private_state, 0.05, params)
    assert cascade.amplification(cap, depth, private_state, 0.05) == pytest.approx(
        params.cascade_ceiling
    )


def test_cap_falls_as_crowding_rises(private_state, params):
    depth = hedging.effective_depth(private_state)
    previous = float("inf")
    for phi in (0.01, 0.02, 0.05, 0.10, 0.20, 0.40):
        cap = cascade.open_interest_cap(depth, private_state, phi, params)
        assert cap < previous
        previous = cap


def test_cap_elasticity_is_exactly_minus_one(private_state, params):
    """Q_max is inversely proportional to phi_1, for every alpha.

    The two enter beta only as the product ``v * phi_1``, so the exponent cancels.
    Revision 1.2 claimed -1/alpha, which came from evaluating F_B at 1 while
    taking the density from phi_1.
    """
    depth = hedging.effective_depth(private_state)
    for alpha in (0.6, 1.0, 1.15, 1.8):
        state = private_state.model_copy(update={"impact_exponent": alpha})
        cap_low = cascade.open_interest_cap(depth, state, 0.02, params)
        cap_high = cascade.open_interest_cap(depth, state, 0.20, params)
        elasticity = math.log(cap_high / cap_low) / math.log(0.20 / 0.02)
        assert elasticity == pytest.approx(-1.0, abs=1e-9)


def test_closed_form_matches_the_general_derivative(private_state, params):
    """The collapsed expression must equal beta(x) evaluated at the reference shock."""
    depth = hedging.effective_depth(private_state)
    for alpha in (0.6, 1.0, 1.15, 1.8):
        for phi in (0.02, 0.05, 0.20):
            state = private_state.model_copy(update={"impact_exponent": alpha})
            general = cascade.amplification_at(
                cascade.REFERENCE_SHOCK, 2 * depth, depth, state, phi
            )
            collapsed = cascade.amplification(2 * depth, depth, state, phi)
            assert collapsed == pytest.approx(general, rel=1e-12)


def test_beta_depends_on_open_interest_and_crowding_only_through_their_product(
    private_state, params
):
    depth = hedging.effective_depth(private_state)
    a = cascade.amplification(4_000_000.0, depth, private_state, 0.05)
    b = cascade.amplification(1_000_000.0, depth, private_state, 0.20)
    assert a == pytest.approx(b)


def test_buffer_closure_is_linear_and_capped(private_state):
    assert cascade.buffer_cdf(cascade.REFERENCE_SHOCK, 0.05) == pytest.approx(0.05)
    assert cascade.buffer_cdf(0.005, 0.05) == pytest.approx(0.025)
    assert cascade.buffer_cdf(0.0, 0.05) == 0.0
    assert cascade.buffer_cdf(1.0, 0.05) == 1.0


def test_superlinear_impact_makes_larger_shocks_worse(private_state):
    """A cap sized at 1% is not conservative against larger shocks when alpha > 1."""
    depth = hedging.effective_depth(private_state)
    state = private_state.model_copy(update={"impact_exponent": 1.15})
    at_reference = cascade.amplification(depth, depth, state, 0.05)
    at_worst = cascade.amplification_at(
        cascade.REFERENCE_SHOCK / 0.05, depth, depth, state, 0.05
    )
    assert at_worst > at_reference
    assert at_worst == pytest.approx(at_reference * 0.05 ** (1.0 - 1.15))


def test_concave_impact_diverges_at_vanishing_shocks(private_state):
    """Why no shock-independent supremum exists for alpha < 1."""
    depth = hedging.effective_depth(private_state)
    state = private_state.model_copy(update={"impact_exponent": 0.6})
    tiny = cascade.amplification_at(1e-6, depth, depth, state, 0.05)
    reference = cascade.amplification(depth, depth, state, 0.05)
    assert tiny > 10 * reference


def test_range_brackets_the_interval(private_state, params):
    depth = hedging.effective_depth(private_state)
    low, high, point = cascade.open_interest_cap_range(depth, private_state, params)
    assert low < high
    assert point is None
    assert low == pytest.approx(
        cascade.open_interest_cap(depth, private_state, private_state.crowding.high, params)
    )
    assert high == pytest.approx(
        cascade.open_interest_cap(depth, private_state, private_state.crowding.low, params)
    )


def test_point_crowding_yields_a_point_cap(private_state, params):
    depth = hedging.effective_depth(private_state)
    state = private_state.model_copy(update={"crowding": Interval.point(0.05)})
    low, high, point = cascade.open_interest_cap_range(depth, state, params)
    assert point is not None
    assert low == pytest.approx(high) == pytest.approx(point)


def test_zero_open_interest_has_no_amplification(private_state):
    depth = hedging.effective_depth(private_state)
    assert cascade.amplification(0.0, depth, private_state, 0.05) == 0.0
