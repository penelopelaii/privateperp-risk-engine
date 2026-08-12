"""Fixtures for the v1 engine tests.

Two states anchor most tests: a benign, liquid, well-marked market that should
support a continuous perp, and an illiquid private-company exposure with a
months-old mark that should not.
"""

from __future__ import annotations

import pytest

from risk_engine.v1 import DEFAULT_POLICY, Interval, MarketState, PolicyParameters


@pytest.fixture
def params() -> PolicyParameters:
    return DEFAULT_POLICY


@pytest.fixture
def liquid_state() -> MarketState:
    return MarketState(
        volatility=0.35,
        spot_depth=20_000_000.0,
        impact_exponent=0.71,
        impact_coefficient=0.0077,
        hedge_depth=19_000_000.0,
        hedge_volatility=0.35,
        hedge_correlation=0.97,
        hedge_ratio=0.95,
        mark_staleness_days=0.0,
        mark_refresh_days=1.0,
        source_count=8,
        source_dispersion=0.001,
        source_correlation=0.3,
        jump_intensity=1.0,
        jump_tail_index=3.0,
        jump_scale=0.03,
        open_interest_long=25_000_000.0,
        open_interest_short=20_000_000.0,
        crowding=Interval(low=0.02, high=0.10),
    )


@pytest.fixture
def private_state() -> MarketState:
    return MarketState(
        volatility=0.97,
        spot_depth=350_000.0,
        impact_exponent=1.15,
        impact_coefficient=0.0703,
        hedge_depth=17_500.0,
        hedge_volatility=0.60,
        hedge_correlation=0.22,
        hedge_ratio=0.05,
        mark_staleness_days=120.0,
        mark_refresh_days=120.0,
        source_count=2,
        source_dispersion=0.20,
        source_correlation=0.6,
        jump_intensity=10.0,
        jump_tail_index=2.0,
        jump_scale=0.05,
        open_interest_long=5_000_000.0,
        open_interest_short=500_000.0,
        crowding=Interval(low=0.02, high=0.20),
    )
