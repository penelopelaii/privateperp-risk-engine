"""Scheduled events and their channels.

The v0 engine treated event proximity as a single penalty. That conflates effects
with opposite signs: approaching a disclosed funding round raises jump risk while
*improving* information, because the round produces a fresh mark. Worse, the
uniform treatment implies every event improves liquidity, which is false -- an
IPO creates an exit only after a lockup, and a recapitalisation can make
historical marks non-comparable and thereby raise uncertainty after the event.

Events therefore act on four independent channels with type-dependent signs.

The functions here are deliberately pure and take primitives rather than a
``MarketState``, so that this module has no dependency on the input model and the
orchestrator stays the only place that assembles state.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class EventType(str, Enum):
    PRICED_ROUND_DISCLOSED = "priced_round_disclosed"
    PRICED_ROUND_UNDISCLOSED = "priced_round_undisclosed"
    DOWN_ROUND_RECAP = "down_round_recap"
    SECONDARY_TENDER = "secondary_tender"
    IPO_LISTING = "ipo_listing"
    LOCKUP_EXPIRY = "lockup_expiry"
    MA_CASH = "ma_cash"
    MA_STOCK = "ma_stock"
    REGULATORY = "regulatory"
    PUBLIC_EARNINGS = "public_earnings"


@dataclass(frozen=True)
class EventChannels:
    """How one event type acts on each channel.

    All values are placeholders expressing the *sign and rough magnitude* from the
    specification's taxonomy table. None is calibrated.
    """

    jump_severity: float
    """Multiplier on the event's own jump scale."""

    improves_information: bool
    """Whether the event produces a fresh mark. Gated on disclosure at use."""

    liquidity_multiplier: float
    """Multiplier on spot depth once the liquidity actually arrives."""

    liquidity_delay_days: float
    """Delay between the event and any liquidity improvement. Non-zero for an IPO
    lockup, which is the case that makes a single 'events improve liquidity'
    rule wrong."""

    breaks_comparability: bool
    """Whether prior marks stop being comparable, raising model risk *after* the
    event rather than lowering it."""

    terminal: bool
    """Whether the contract should settle rather than continue."""


COMPARABILITY_BREAK_DISPERSION_MULTIPLIER = 2.0
"""Inflation applied to source dispersion when an event breaks comparability."""


EVENT_CHANNELS: dict[EventType, EventChannels] = {
    EventType.PRICED_ROUND_DISCLOSED: EventChannels(1.0, True, 1.0, 0.0, False, False),
    # Pure downside: jump risk with no offsetting information gain.
    EventType.PRICED_ROUND_UNDISCLOSED: EventChannels(1.0, False, 1.0, 0.0, False, False),
    EventType.DOWN_ROUND_RECAP: EventChannels(2.0, True, 1.0, 0.0, True, False),
    # Temporary: the exit exists for the tender window and then closes again.
    EventType.SECONDARY_TENDER: EventChannels(0.6, True, 1.5, 0.0, False, False),
    # Liquidity arrives only after the lockup, while hedgeability can improve sooner.
    EventType.IPO_LISTING: EventChannels(2.0, True, 3.0, 180.0, False, False),
    EventType.LOCKUP_EXPIRY: EventChannels(0.3, False, 1.5, 0.0, False, False),
    EventType.MA_CASH: EventChannels(2.5, True, 1.0, 0.0, False, True),
    EventType.MA_STOCK: EventChannels(2.0, True, 1.0, 0.0, True, False),
    EventType.REGULATORY: EventChannels(2.0, True, 1.0, 0.0, False, False),
    EventType.PUBLIC_EARNINGS: EventChannels(1.0, True, 1.0, 0.0, False, False),
}


class ScheduledEvent(BaseModel):
    """A repricing event with a known date."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: EventType
    days_until: float = Field(..., ge=0.0, description="tau_E, calendar days.")
    jump_scale: float = Field(
        ..., gt=0.0, description="sigma_E: expected log-return move at the event."
    )
    disclosed: bool = Field(
        default=True,
        description="Whether the resulting price will be published. An undisclosed "
        "outcome improves nothing, whatever the event type.",
    )

    @property
    def channels(self) -> EventChannels:
        return EVENT_CHANNELS[self.type]


def effective_refresh_days(event: ScheduledEvent | None, mark_refresh_days: float) -> float:
    """Bring the expected next mark forward if the event will publish one.

    This is the information channel: a disclosed event guarantees a refresh no
    later than shortly after it occurs, so uncertainty *falls* as the event
    approaches even while jump risk rises. Gated on disclosure, so an undisclosed
    round leaves the refresh interval untouched.
    """
    if event is None:
        return mark_refresh_days
    if not (event.channels.improves_information and event.disclosed):
        return mark_refresh_days
    return min(mark_refresh_days, event.days_until + 1.0)


def dispersion_multiplier(event: ScheduledEvent | None) -> float:
    """Inflate dispersion when an event will break the comparability of marks.

    A recapitalisation produces a fresh price that is *less* informative about the
    old one, because the preference stack changed underneath it.
    """
    if event is None or not event.channels.breaks_comparability:
        return 1.0
    return COMPARABILITY_BREAK_DISPERSION_MULTIPLIER


def depth_multiplier(event: ScheduledEvent | None, horizon_days: float) -> float:
    """Apply an event's liquidity improvement only once it has actually arrived.

    An IPO 30 days away with a 180-day lockup contributes nothing to a 5-day
    unwind horizon, which is exactly the case a uniform "events improve
    liquidity" rule gets wrong.
    """
    if event is None:
        return 1.0
    available_after = event.days_until + event.channels.liquidity_delay_days
    return event.channels.liquidity_multiplier if available_after <= horizon_days else 1.0


def unavoidable_jump_loss(event: ScheduledEvent | None, response_horizon_days: float) -> float:
    """Loss from an event jump that cannot be exited ahead of.

    Active when the response horizon reaches the event date: if the venue cannot
    act before it happens, the position is exposed to it.
    """
    if event is None or event.days_until > response_horizon_days:
        return 0.0
    return 1.0 - math.exp(-event.channels.jump_severity * event.jump_scale)


def is_terminal(event: ScheduledEvent | None) -> bool:
    """Whether the event ends the contract rather than repricing it."""
    return event is not None and event.channels.terminal
