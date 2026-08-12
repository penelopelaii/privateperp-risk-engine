"""The v0 compatibility adapter."""

from __future__ import annotations

import json

from backend.tests.conftest import ILLIQUID_PRIVATE_EXPOSURE, LIQUID_PUBLIC_ASSET
from risk_engine import RiskInputs, evaluate_risk
from risk_engine.v0_adapter import adapter_provenance, to_market_state
from risk_engine.v1 import Provenance, evaluate_risk_v1


def test_adapter_produces_a_valid_state():
    state = to_market_state(RiskInputs(**LIQUID_PUBLIC_ASSET))
    assert state.volatility > 0.0
    assert state.spot_depth == LIQUID_PUBLIC_ASSET["market_depth"]


def test_adapter_round_trips_every_synthetic_profile():
    with open("data/synthetic/asset_profiles.json") as handle:
        profiles = json.load(handle)["profiles"]
    for profile in profiles:
        outputs = evaluate_risk_v1(to_market_state(RiskInputs(**profile["inputs"])))
        assert outputs.margin_diagnostics.required_initial_margin > 0.0


def test_inferred_volatility_is_tagged_not_calibrated():
    """L2: the adapter may infer sigma, but never presents it as measured."""
    provenance = adapter_provenance()
    assert provenance["volatility"] is Provenance.INFERRED_FROM_V0


def test_fitted_impact_parameters_are_tagged_as_synthetic():
    provenance = adapter_provenance()
    assert provenance["impact_exponent"] is Provenance.FITTED_SYNTHETIC
    assert provenance["impact_coefficient"] is Provenance.FITTED_SYNTHETIC


def test_adapted_evaluation_is_flagged_as_assumed():
    outputs = evaluate_risk_v1(
        to_market_state(RiskInputs(**LIQUID_PUBLIC_ASSET)),
        input_provenance=adapter_provenance(),
    )
    assert outputs.contains_assumed_inputs


def test_crowding_is_always_an_interval():
    """v0 cannot observe crowding, so it can never produce a point cap."""
    state = to_market_state(RiskInputs(**ILLIQUID_PRIVATE_EXPOSURE))
    assert not state.crowding.is_point

    outputs = evaluate_risk_v1(state)
    assert outputs.size_limits.open_interest_cap_point is None


def test_impact_parameters_track_liquidity():
    """Thinner markets get a steeper, more convex impact curve."""
    liquid = to_market_state(RiskInputs(**LIQUID_PUBLIC_ASSET))
    illiquid = to_market_state(RiskInputs(**ILLIQUID_PRIVATE_EXPOSURE))
    assert illiquid.impact_exponent > liquid.impact_exponent
    assert illiquid.impact_coefficient > liquid.impact_coefficient


def test_v0_engine_is_unaffected_by_the_adapter():
    """v0 behaviour must be untouched by v1's existence."""
    inputs = RiskInputs(**ILLIQUID_PRIVATE_EXPOSURE)
    before = evaluate_risk(inputs)
    to_market_state(inputs)
    after = evaluate_risk(inputs)
    assert before == after


def test_adapter_disagrees_with_v0_on_the_private_profile():
    """The whole point: v0 quotes a tradable number where v1 finds none."""
    inputs = RiskInputs(**ILLIQUID_PRIVATE_EXPOSURE)
    v0 = evaluate_risk(inputs)
    v1 = evaluate_risk_v1(to_market_state(inputs))

    assert v0.recommended_max_leverage > 1.0
    assert not v1.viable_as_continuous_perp
