"""Contract tests for ``POST /risk/v1/evaluate``.

The v1 endpoint's job is to transport the whole assessment without quietly
simplifying it. Most of these assert that the parts a consumer is most likely to
drop — the regimes, the provenance, the unclamped diagnostics — survive the round
trip.
"""

from __future__ import annotations

VIABLE_STATE = {
    "volatility": 0.35,
    "spot_depth": 20_000_000.0,
    "impact_exponent": 0.71,
    "impact_coefficient": 0.0077,
    "hedge_depth": 19_000_000.0,
    "hedge_volatility": 0.35,
    "hedge_correlation": 0.97,
    "hedge_ratio": 0.95,
    "mark_staleness_days": 0.0,
    "mark_refresh_days": 1.0,
    "source_count": 8,
    "source_dispersion": 0.001,
    "source_correlation": 0.3,
    "jump_intensity": 1.0,
    "jump_tail_index": 3.0,
    "jump_scale": 0.03,
    "open_interest_long": 25_000_000.0,
    "open_interest_short": 20_000_000.0,
    "crowding": {"low": 0.02, "high": 0.10},
}

NON_VIABLE_STATE = {
    **VIABLE_STATE,
    "volatility": 0.97,
    "spot_depth": 350_000.0,
    "impact_exponent": 1.15,
    "impact_coefficient": 0.0703,
    "hedge_depth": 17_500.0,
    "hedge_volatility": 0.60,
    "hedge_correlation": 0.22,
    "hedge_ratio": 0.05,
    "mark_staleness_days": 120.0,
    "mark_refresh_days": 120.0,
    "source_count": 2,
    "source_dispersion": 0.20,
    "source_correlation": 0.6,
    "jump_intensity": 10.0,
    "jump_tail_index": 2.0,
    "jump_scale": 0.05,
    "crowding": {"low": 0.02, "high": 0.20},
}


def post_v1(client, state, policy=None):
    body = {"state": state}
    if policy is not None:
        body["policy"] = policy
    return client.post("/risk/v1/evaluate", json=body)


def test_viable_market_returns_tradable_parameters(client):
    response = post_v1(client, VIABLE_STATE)
    assert response.status_code == 200

    payload = response.json()["outputs"]
    assert payload["viable_as_continuous_perp"] is True
    assert payload["recommended_mechanism"] == "continuous_perp"
    assert payload["tradable"]["max_leverage"] >= 1.0
    assert payload["triggered_regimes"] == []


def test_non_viable_market_returns_null_tradable(client):
    payload = post_v1(client, NON_VIABLE_STATE).json()["outputs"]
    assert payload["viable_as_continuous_perp"] is False
    assert payload["tradable"] is None
    assert payload["recommended_mechanism"] in {
        "periodic_auction",
        "settled_forward",
        "not_listable",
    }


def test_unconstrained_margin_survives_the_wire(client):
    """L3: a margin above notional must reach the client, not be clamped en route."""
    diagnostics = post_v1(client, NON_VIABLE_STATE).json()["outputs"]["margin_diagnostics"]
    assert diagnostics["required_initial_margin"] > 1.0
    assert diagnostics["implied_leverage"] < 1.0


def test_triggered_regimes_are_transported_with_their_measurements(client):
    regimes = post_v1(client, NON_VIABLE_STATE).json()["outputs"]["triggered_regimes"]
    assert regimes
    for regime in regimes:
        assert regime["id"] in {"R1", "R2", "R3"}
        assert regime["description"]
        assert "measured" in regime
        assert "threshold" in regime


def test_size_limits_are_returned_even_when_not_viable(client):
    """An auction or a forward needs limits too."""
    limits = post_v1(client, NON_VIABLE_STATE).json()["outputs"]["size_limits"]
    assert limits["position_limit"] > 0.0
    assert limits["open_interest_cap_low"] < limits["open_interest_cap_high"]
    assert limits["open_interest_cap_point"] is None


def test_point_crowding_yields_a_point_cap(client):
    state = {**VIABLE_STATE, "crowding": {"low": 0.05, "high": 0.05}}
    limits = post_v1(client, state).json()["outputs"]["size_limits"]
    assert limits["open_interest_cap_point"] is not None


def test_dimensions_are_returned(client):
    dimensions = post_v1(client, VIABLE_STATE).json()["outputs"]["dimensions"]
    for field in (
        "price_uncertainty",
        "effective_depth",
        "liquidation_cost_at_limit",
        "unwind_days_at_limit",
        "residual_volatility",
        "cascade_beta_at_cap",
        "dispersion_diagnostic_ratio",
    ):
        assert field in dimensions


def test_provenance_marks_http_supplied_state_as_assumed(client):
    """Nothing arriving from a slider is a measurement."""
    payload = post_v1(client, VIABLE_STATE).json()["outputs"]
    assert payload["contains_assumed_inputs"] is True
    assert payload["provenance"]["volatility"] == "assumed"


def test_policy_defaults_are_echoed_back(client):
    payload = post_v1(client, VIABLE_STATE).json()
    assert payload["policy"]["max_unwind_days"] == 5.0
    assert payload["state"]["volatility"] == VIABLE_STATE["volatility"]


def test_policy_can_be_overridden(client):
    """Tightening the venue's own appetite must move the limits."""
    default = post_v1(client, VIABLE_STATE).json()
    tightened = post_v1(client, VIABLE_STATE, policy={"max_unwind_days": 1.0}).json()

    assert tightened["policy"]["max_unwind_days"] == 1.0
    assert (
        tightened["outputs"]["size_limits"]["position_limit"]
        < default["outputs"]["size_limits"]["position_limit"]
    )


def test_invalid_state_is_rejected(client):
    """Volatility is required and must be positive."""
    assert post_v1(client, {**VIABLE_STATE, "volatility": 0.0}).status_code == 422
    assert post_v1(client, {k: v for k, v in VIABLE_STATE.items() if k != "volatility"}).status_code == 422


def test_single_source_with_dispersion_is_rejected(client):
    """A model-level validator, surfaced as a 422 rather than a 500."""
    state = {**VIABLE_STATE, "source_count": 1, "source_dispersion": 0.01}
    assert post_v1(client, state).status_code == 422


def test_v1_endpoint_does_not_disturb_v0(client, liquid_inputs):
    """The two engines share a process and must not share state."""
    before = client.post("/risk/evaluate", json={"inputs": liquid_inputs.model_dump()}).json()
    post_v1(client, NON_VIABLE_STATE)
    after = client.post("/risk/evaluate", json={"inputs": liquid_inputs.model_dump()}).json()
    assert before == after
