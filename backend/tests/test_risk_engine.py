"""Behavioural guarantees of the engine.

These assert direction and bounds rather than exact numbers, since the v0
parameterisation is a placeholder and its constants are expected to change.
"""

from __future__ import annotations

from risk_engine import evaluate_risk
from risk_engine.risk_score import COMPONENT_WEIGHTS


def test_component_weights_sum_to_one():
    assert sum(COMPONENT_WEIGHTS.values()) == 1.0


def test_outputs_are_within_declared_bounds(illiquid_inputs):
    outputs = evaluate_risk(illiquid_inputs)
    assert 0.0 <= outputs.risk_score <= 100.0
    assert 0.0 < outputs.initial_margin <= 1.0
    assert outputs.maintenance_margin <= outputs.initial_margin
    assert outputs.position_limit <= outputs.open_interest_cap
    assert outputs.recommended_max_leverage >= 1.0


def test_illiquid_market_is_scored_riskier_than_liquid_one(liquid_inputs, illiquid_inputs):
    assert evaluate_risk(illiquid_inputs).risk_score > evaluate_risk(liquid_inputs).risk_score


def test_illiquid_market_receives_tighter_parameters(liquid_inputs, illiquid_inputs):
    liquid = evaluate_risk(liquid_inputs)
    illiquid = evaluate_risk(illiquid_inputs)

    assert illiquid.recommended_max_leverage < liquid.recommended_max_leverage
    assert illiquid.initial_margin > liquid.initial_margin
    assert illiquid.maintenance_margin > liquid.maintenance_margin
    assert illiquid.liquidation_buffer > liquid.liquidation_buffer
    assert illiquid.open_interest_cap < liquid.open_interest_cap


def test_score_breakdown_reconstructs_the_score(illiquid_inputs):
    outputs = evaluate_risk(illiquid_inputs)
    assert sum(outputs.score_breakdown.values()) == outputs.risk_score
    assert set(outputs.score_breakdown) == set(COMPONENT_WEIGHTS)


# --------------------------------------------------------------------------
# Relationship-specific guarantees.
#
# These replace a single blanket monotonicity test. The v1 specification
# establishes that monotonicity is desirable per-relationship rather than
# globally, so each guarantee is asserted on its own and the relationships that
# are deliberately NOT monotone are characterised rather than enforced.
# See docs/model_v1_spec.md, "Consistency guarantees".
# --------------------------------------------------------------------------


def test_initial_margin_exceeds_maintenance_margin(liquid_inputs, illiquid_inputs):
    for inputs in (liquid_inputs, illiquid_inputs):
        outputs = evaluate_risk(inputs)
        assert outputs.initial_margin > outputs.maintenance_margin


def test_leverage_decreases_in_jump_risk(liquid_inputs):
    previous = None
    for jump in [0.0, 0.25, 0.5, 0.75, 1.0]:
        outputs = evaluate_risk(liquid_inputs.model_copy(update={"jump_risk": jump}))
        if previous is not None:
            assert outputs.recommended_max_leverage <= previous
        previous = outputs.recommended_max_leverage


def test_margin_increases_as_price_discovery_degrades(liquid_inputs):
    previous = None
    for staleness in [0.0, 7.0, 30.0, 90.0, 365.0]:
        outputs = evaluate_risk(
            liquid_inputs.model_copy(update={"price_staleness_days": staleness})
        )
        if previous is not None:
            assert outputs.initial_margin >= previous
        previous = outputs.initial_margin


def test_size_caps_increase_in_market_depth(illiquid_inputs):
    previous = None
    for depth in [100_000.0, 500_000.0, 2_000_000.0, 10_000_000.0]:
        outputs = evaluate_risk(illiquid_inputs.model_copy(update={"market_depth": depth}))
        if previous is not None:
            assert outputs.open_interest_cap > previous
        previous = outputs.open_interest_cap


def test_liquidation_buffer_increases_in_staleness(liquid_inputs):
    fresh = evaluate_risk(liquid_inputs.model_copy(update={"price_staleness_days": 0.0}))
    stale = evaluate_risk(liquid_inputs.model_copy(update={"price_staleness_days": 90.0}))
    assert stale.liquidation_buffer > fresh.liquidation_buffer


def test_v0_saturates_in_open_interest(illiquid_inputs):
    """Characterisation, not a guarantee: v0 is blind above 5x market depth.

    The crowding component clamps at CROWDING_DEPTH_MULTIPLE, so a market at 5x
    depth and one at 100x depth receive identical parameters. v1 replaces this
    with an unbounded convex cascade term; this test pins the v0 behaviour so
    the difference is visible rather than surprising.
    """
    depth = illiquid_inputs.market_depth
    at_5x = evaluate_risk(illiquid_inputs.model_copy(update={"current_open_interest": 5 * depth}))
    at_100x = evaluate_risk(
        illiquid_inputs.model_copy(update={"current_open_interest": 100 * depth})
    )
    assert at_5x.risk_score == at_100x.risk_score
