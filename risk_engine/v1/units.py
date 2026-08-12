"""Time and scale conventions.

The only place in v1 where a day/year conversion appears. Revision 1.1 of the
specification found that mixing annualised rates with day-valued horizons was the
single most damaging class of bug in v0 -- at 120 days of staleness it reported
1061% price uncertainty instead of 55.6% -- so the conversions are centralised
here and every other module is expected to call them rather than divide by a
literal.
"""

from __future__ import annotations

# Calendar, not trading, days (specification L4). Information decay on an asset
# that reprices a few times a year is a calendar process, and a single convention
# removes a whole class of bug. All volatility and jump-intensity inputs must be
# calendar-annualised.
CALENDAR_DAYS_PER_YEAR = 365.0

# Reference period that makes the impact curve's argument dimensionless. Depth is
# a rate (USD/day), so ``notional / depth`` is a time; dividing by one day turns
# it into "days of depth". The fitted impact coefficients are only transferable
# alongside this constant.
IMPACT_REFERENCE_PERIOD_DAYS = 1.0

# Floor on the window used by the dispersion diagnostic only. See
# ``uncertainty.dispersion_diagnostic_ratio`` for why this exists and for why it
# is deliberately not applied to the staleness variance term.
MIN_INFORMATION_HORIZON_DAYS = 1.0


def years(days: float) -> float:
    """Convert a horizon in calendar days to a fraction of a year."""
    return days / CALENDAR_DAYS_PER_YEAR


def days(years_: float) -> float:
    """Convert a fraction of a year to calendar days."""
    return years_ * CALENDAR_DAYS_PER_YEAR


def days_of_depth(notional_usd: float, depth_usd_per_day: float) -> float:
    """Express a position as a dimensionless multiple of one day's depth.

    This is the ``v`` of the specification: ``q / (D_eff * T_ref)``.
    """
    if depth_usd_per_day <= 0.0:
        raise ValueError("depth must be strictly positive to express days of depth")
    return notional_usd / (depth_usd_per_day * IMPACT_REFERENCE_PERIOD_DAYS)
