"""Input validation for the v1 market state."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from risk_engine.v1 import Interval, MarketState

VALID = {
    "volatility": 0.5,
    "spot_depth": 1_000_000.0,
    "impact_exponent": 1.0,
    "impact_coefficient": 0.02,
    "mark_staleness_days": 5.0,
    "mark_refresh_days": 5.0,
    "jump_intensity": 2.0,
    "jump_tail_index": 2.5,
    "jump_scale": 0.05,
    "crowding": Interval(low=0.02, high=0.20),
}


def test_valid_state_constructs():
    assert MarketState(**VALID).volatility == 0.5


def test_volatility_must_be_positive():
    """L2 and the hedge-capacity denominator: zero volatility is out of domain."""
    with pytest.raises(ValidationError):
        MarketState(**{**VALID, "volatility": 0.0})


def test_volatility_is_required():
    payload = {k: v for k, v in VALID.items() if k != "volatility"}
    with pytest.raises(ValidationError):
        MarketState(**payload)


def test_crowding_is_required():
    payload = {k: v for k, v in VALID.items() if k != "crowding"}
    with pytest.raises(ValidationError):
        MarketState(**payload)


def test_dispersion_is_rejected_with_a_single_source():
    """One source cannot disagree with itself."""
    with pytest.raises(ValidationError):
        MarketState(**{**VALID, "source_count": 1, "source_dispersion": 0.0})


def test_dispersion_is_required_with_several_sources():
    with pytest.raises(ValidationError):
        MarketState(**{**VALID, "source_count": 3})


def test_hedge_fields_required_when_a_hedge_venue_exists():
    with pytest.raises(ValidationError):
        MarketState(**{**VALID, "hedge_depth": 100.0})


def test_interval_rejects_inverted_bounds():
    with pytest.raises(ValidationError):
        Interval(low=0.5, high=0.1)


def test_interval_point_helper():
    point = Interval.point(0.05)
    assert point.is_point
    assert point.midpoint == 0.05


def test_crowding_must_be_a_share():
    with pytest.raises(ValidationError):
        MarketState(**{**VALID, "crowding": Interval(low=0.1, high=1.5)})


def test_crowding_must_be_positive():
    with pytest.raises(ValidationError):
        MarketState(**{**VALID, "crowding": Interval(low=0.0, high=0.2)})


def test_directional_open_interest_aggregates():
    state = MarketState(**VALID, open_interest_long=3.0, open_interest_short=1.0)
    assert state.gross_open_interest == 4.0
    assert state.net_open_interest == 2.0
