"""Time and scale conventions."""

from __future__ import annotations

import pytest

from risk_engine.v1 import units


def test_calendar_convention_is_365():
    """L4: v1 and every simulation share one convention."""
    assert units.CALENDAR_DAYS_PER_YEAR == 365.0


def test_day_year_round_trip():
    assert units.days(units.years(45.0)) == pytest.approx(45.0)


def test_one_year_is_one():
    assert units.years(365.0) == pytest.approx(1.0)


def test_days_of_depth_is_dimensionless_ratio():
    """A position equal to one day of depth is 1.0 days of depth."""
    assert units.days_of_depth(500_000.0, 500_000.0) == pytest.approx(1.0)
    assert units.days_of_depth(2_500_000.0, 500_000.0) == pytest.approx(5.0)


def test_days_of_depth_rejects_zero_depth():
    with pytest.raises(ValueError):
        units.days_of_depth(1.0, 0.0)


def test_simulations_share_the_convention():
    """The prerequisite change required by L4, asserted rather than assumed."""
    from simulations import jump_risk, oracle_staleness

    assert jump_risk.CALENDAR_DAYS_PER_YEAR == units.CALENDAR_DAYS_PER_YEAR
    assert oracle_staleness.CALENDAR_DAYS_PER_YEAR == units.CALENDAR_DAYS_PER_YEAR
