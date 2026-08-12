"""Liquidation buffer.

The buffer is the cushion between the point where a position is flagged and the
point where the venue is actually underwater. It exists to absorb the two things
that go wrong during an unwind on an illiquid underlying: the mark is stale or
uncertain, and the exit itself moves the price.
"""

from __future__ import annotations

# Cushion in a zero-risk market, as a fraction of maintenance margin.
BASE_BUFFER = 0.10

# Additional cushion attributable to the composite score at maximum risk.
BUFFER_RISK_RANGE = 0.40

# Additional cushion attributable specifically to gap risk, which the composite
# score under-weights: a jump can skip the liquidation price entirely.
BUFFER_JUMP_RANGE = 0.25

MAX_BUFFER = 1.00


def liquidation_buffer(risk_score: float, jump_risk: float) -> float:
    """Return the liquidation cushion as a fraction of maintenance margin.

    Placeholder implementation: a base cushion plus linear terms in the
    composite score and in jump risk, capped at 100% of maintenance margin.

    Future work: this should be sized from the simulated distribution of
    shortfall at liquidation (see ``simulations/jump_risk.py`` and
    ``simulations/liquidation_cascade.py``) so the buffer targets an explicit
    probability of the insurance fund taking a loss.
    """
    normalised = min(max(risk_score, 0.0), 100.0) / 100.0
    jump = min(max(jump_risk, 0.0), 1.0)
    buffer = BASE_BUFFER + BUFFER_RISK_RANGE * normalised + BUFFER_JUMP_RANGE * jump
    return min(buffer, MAX_BUFFER)
