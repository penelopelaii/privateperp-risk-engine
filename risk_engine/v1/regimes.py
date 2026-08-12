"""Preconditions for continuous mark-based margining.

Continuous margining is a mechanism with preconditions, not a parameter setting
that can always be tightened. Three of them are checked here, and they fail for
different reasons: R1 says the collateral requirement has eliminated leverage,
R2 says the state is not observable often enough to manage, and R3 says the
trigger is more noise than signal.

Only R1 is about the *amount* of collateral. That is why the response to R2 or R3
is a different decision cadence rather than a higher number.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class Mechanism(str, Enum):
    """What instrument, if any, this market can support."""

    CONTINUOUS_PERP = "continuous_perp"
    PERIODIC_AUCTION = "periodic_auction"
    SETTLED_FORWARD = "settled_forward"
    NOT_LISTABLE = "not_listable"


class RegimeId(str, Enum):
    R1 = "R1"
    R2 = "R2"
    R3 = "R3"


class RegimeTrigger(BaseModel):
    """One failed precondition, carrying the numbers that failed it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: RegimeId
    description: str
    measured: float
    threshold: float


def evaluate_regimes(
    *,
    initial_margin: float,
    maintenance_margin: float,
    refresh_days: float,
    unwind_days: float,
    price_uncertainty: float,
    jump_loss_over_refresh: float,
    z_spurious: float,
) -> list[RegimeTrigger]:
    """Check all three preconditions and return those that failed."""
    triggered: list[RegimeTrigger] = []

    if initial_margin >= 1.0:
        triggered.append(
            RegimeTrigger(
                id=RegimeId.R1,
                description=(
                    "Required initial margin meets or exceeds notional, so the product "
                    "is not leveraged. A contract demanding more collateral than the "
                    "position is worth is a prepaid forward with extra steps, and a "
                    "worse one: it keeps funding payments and liquidation risk while "
                    "offering no leverage."
                ),
                measured=initial_margin,
                threshold=1.0,
            )
        )

    if refresh_days >= unwind_days:
        triggered.append(
            RegimeTrigger(
                id=RegimeId.R2,
                description=(
                    "The mark does not refresh even once during a full unwind, so there "
                    "is no state feedback while the venue is acting. Continuous "
                    "margining presumes a continuously observable state. Independent of "
                    "volatility and of margin level: no collateral schedule makes an "
                    "unobservable state observable."
                ),
                measured=refresh_days,
                threshold=unwind_days,
            )
        )

    required_buffer = z_spurious * price_uncertainty + jump_loss_over_refresh
    available_cushion = initial_margin - maintenance_margin
    if required_buffer > available_cushion:
        triggered.append(
            RegimeTrigger(
                id=RegimeId.R3,
                description=(
                    "The buffer needed to keep liquidations defensible does not fit "
                    "inside the cushion between initial and maintenance margin. "
                    "Liquidation decisions would be close to uncorrelated with actual "
                    "solvency, and raising margin does not help: margin governs the "
                    "loss that can be absorbed, not the accuracy of the measurement "
                    "that triggers absorption."
                ),
                measured=required_buffer,
                threshold=available_cushion,
            )
        )

    return triggered


def select_mechanism(
    triggered: list[RegimeTrigger], refresh_days: float, settlement_horizon_days: float
) -> Mechanism:
    """Map failed preconditions onto the instrument that can still work.

    R2 or R3 alone means the *decisions* are unsound while the *collateral* is
    adequate, so the fix is to decide only when a price exists. R1 means
    collateral has eliminated leverage, so the fix is to stop pretending the
    instrument is leveraged. If no mark is expected within the settlement
    horizon, even a forward has nothing to settle against.
    """
    ids = {trigger.id for trigger in triggered}

    if not ids:
        return Mechanism.CONTINUOUS_PERP
    if RegimeId.R1 in ids:
        if refresh_days > settlement_horizon_days:
            return Mechanism.NOT_LISTABLE
        return Mechanism.SETTLED_FORWARD
    return Mechanism.PERIODIC_AUCTION
