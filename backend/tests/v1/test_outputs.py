"""Output schema behaviour, especially under non-viability."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from risk_engine.v1 import Mechanism, TradableParameters, evaluate_risk_v1


def test_viable_market_returns_tradable_parameters(liquid_state, params):
    outputs = evaluate_risk_v1(liquid_state, params)
    assert outputs.viable_as_continuous_perp
    assert outputs.recommended_mechanism is Mechanism.CONTINUOUS_PERP
    assert outputs.tradable is not None
    assert outputs.tradable.max_leverage >= 1.0


def test_non_viable_market_returns_no_tradable_parameters(private_state, params):
    """A clamped sub-1x leverage could be rendered by accident; None cannot."""
    outputs = evaluate_risk_v1(private_state, params)
    assert not outputs.viable_as_continuous_perp
    assert outputs.tradable is None


def test_required_margin_is_never_clamped(private_state, params):
    """L3: the numeric result is reported even above 100% of notional."""
    outputs = evaluate_risk_v1(private_state, params)
    assert outputs.margin_diagnostics.required_initial_margin > 1.0


def test_implied_leverage_below_one_is_reported_as_a_diagnostic(private_state, params):
    outputs = evaluate_risk_v1(private_state, params)
    assert outputs.margin_diagnostics.implied_leverage < 1.0
    assert outputs.tradable is None


def test_tradable_parameters_cannot_hold_sub_unit_leverage():
    """The schema itself refuses to express the thing L3 forbids."""
    with pytest.raises(ValidationError):
        TradableParameters(
            max_leverage=0.4, initial_margin=0.5, maintenance_margin=0.3, liquidation_buffer=0.1
        )


def test_tradable_parameters_cannot_hold_margin_above_notional():
    with pytest.raises(ValidationError):
        TradableParameters(
            max_leverage=1.0, initial_margin=1.5, maintenance_margin=0.3, liquidation_buffer=0.1
        )


def test_non_viable_market_still_reports_size_limits(private_state, params):
    """An auction or forward needs limits too, and they do not depend on margining."""
    outputs = evaluate_risk_v1(private_state, params)
    assert outputs.size_limits.position_limit > 0.0
    assert outputs.size_limits.open_interest_cap_high > 0.0


def test_non_viable_market_still_reports_dimensions(private_state, params):
    outputs = evaluate_risk_v1(private_state, params)
    assert outputs.dimensions.price_uncertainty > 0.0
    assert outputs.dimensions.effective_depth > 0.0


def test_triggered_regimes_carry_their_measurements(private_state, params):
    outputs = evaluate_risk_v1(private_state, params)
    assert outputs.triggered_regimes
    for trigger in outputs.triggered_regimes:
        assert trigger.description
        assert trigger.measured != trigger.threshold


def test_viable_market_triggers_nothing(liquid_state, params):
    assert evaluate_risk_v1(liquid_state, params).triggered_regimes == []


def test_initial_margin_exceeds_maintenance_margin(liquid_state, private_state, params):
    for state in (liquid_state, private_state):
        diagnostics = evaluate_risk_v1(state, params).margin_diagnostics
        assert diagnostics.required_initial_margin > diagnostics.required_maintenance_margin


def test_open_interest_cap_is_a_range_for_an_interval(private_state, params):
    outputs = evaluate_risk_v1(private_state, params)
    assert outputs.size_limits.open_interest_cap_point is None
    assert outputs.size_limits.open_interest_cap_low < outputs.size_limits.open_interest_cap_high


def test_every_evaluation_is_flagged_as_containing_assumptions(liquid_state, params):
    """True for everything this repository can currently produce."""
    assert evaluate_risk_v1(liquid_state, params).contains_assumed_inputs


def test_engine_version_is_reported(liquid_state, params):
    assert evaluate_risk_v1(liquid_state, params).engine_version
