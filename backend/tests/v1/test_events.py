"""Event channels, and the cases a uniform event penalty gets wrong."""

from __future__ import annotations

import pytest

from risk_engine.v1 import events
from risk_engine.v1.events import EventType, ScheduledEvent


def event(event_type: EventType, days_until: float = 10.0, **kwargs) -> ScheduledEvent:
    return ScheduledEvent(type=event_type, days_until=days_until, jump_scale=0.20, **kwargs)


def test_no_event_leaves_every_channel_untouched():
    assert events.effective_refresh_days(None, 30.0) == 30.0
    assert events.dispersion_multiplier(None) == 1.0
    assert events.depth_multiplier(None, 5.0) == 1.0
    assert events.unavoidable_jump_loss(None, 1.0) == 0.0


def test_disclosed_event_brings_the_next_mark_forward():
    """The information channel: uncertainty falls as a disclosure approaches."""
    assert events.effective_refresh_days(
        event(EventType.PRICED_ROUND_DISCLOSED, days_until=5.0), 90.0
    ) == pytest.approx(6.0)


def test_undisclosed_round_improves_nothing():
    """Pure downside: jump risk with no offsetting information gain."""
    assert (
        events.effective_refresh_days(event(EventType.PRICED_ROUND_UNDISCLOSED), 90.0) == 90.0
    )


def test_disclosure_flag_overrides_the_event_type():
    """A normally-publishing event that will not publish improves nothing."""
    quiet = event(EventType.PRICED_ROUND_DISCLOSED, days_until=5.0, disclosed=False)
    assert events.effective_refresh_days(quiet, 90.0) == 90.0


def test_refresh_is_never_pushed_backwards():
    """A distant event must not make a frequently-marked asset look worse."""
    assert events.effective_refresh_days(
        event(EventType.PRICED_ROUND_DISCLOSED, days_until=300.0), 1.0
    ) == pytest.approx(1.0)


def test_ipo_liquidity_is_delayed_by_the_lockup():
    """The case that makes 'events improve liquidity' wrong as a blanket rule."""
    ipo = event(EventType.IPO_LISTING, days_until=30.0)
    assert events.depth_multiplier(ipo, horizon_days=5.0) == 1.0
    assert events.depth_multiplier(ipo, horizon_days=400.0) > 1.0


def test_tender_liquidity_arrives_immediately():
    tender = event(EventType.SECONDARY_TENDER, days_until=2.0)
    assert events.depth_multiplier(tender, horizon_days=5.0) > 1.0


def test_recap_breaks_comparability_and_raises_dispersion():
    """A fresh price that is less informative about the old one."""
    assert events.dispersion_multiplier(event(EventType.DOWN_ROUND_RECAP)) > 1.0
    assert events.dispersion_multiplier(event(EventType.PRICED_ROUND_DISCLOSED)) == 1.0


def test_jump_is_unavoidable_only_inside_the_response_horizon():
    imminent = event(EventType.PUBLIC_EARNINGS, days_until=0.5)
    distant = event(EventType.PUBLIC_EARNINGS, days_until=30.0)
    assert events.unavoidable_jump_loss(imminent, response_horizon_days=1.0) > 0.0
    assert events.unavoidable_jump_loss(distant, response_horizon_days=1.0) == 0.0


def test_jump_loss_respects_limited_liability():
    huge = ScheduledEvent(type=EventType.MA_CASH, days_until=0.0, jump_scale=5.0)
    assert 0.0 < events.unavoidable_jump_loss(huge, 1.0) < 1.0


def test_cash_acquisition_is_terminal():
    assert events.is_terminal(event(EventType.MA_CASH))
    assert not events.is_terminal(event(EventType.PUBLIC_EARNINGS))


def test_every_event_type_has_channels():
    for event_type in EventType:
        assert event_type in events.EVENT_CHANNELS
