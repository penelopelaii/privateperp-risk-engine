"""Size limits: market-wide open interest and per-account position.

Margin protects the venue against price moves; size limits protect it against
the impossibility of exiting. On an illiquid underlying these are the binding
constraint, because no margin level makes a position safe if unwinding it would
itself move the price several percent.
"""

from __future__ import annotations

# Open interest permitted per unit of hedging depth in a zero-risk market.
BASE_DEPTH_MULTIPLE = 10.0

# Fraction of the depth multiple removed at maximum risk score.
DEPTH_MULTIPLE_RISK_SENSITIVITY = 0.90

# Share of the market-wide cap a single account may hold in a benign market.
BASE_ACCOUNT_SHARE = 0.10

# Floor on that share, so limits stay meaningful in the riskiest markets.
MIN_ACCOUNT_SHARE = 0.02


def open_interest_cap(market_depth: float, risk_score: float) -> float:
    """Return the market-wide open interest cap in USD notional.

    Placeholder implementation: a multiple of hedging depth that shrinks
    linearly with risk, from 10x depth at score 0 to 1x depth at score 100.

    Future work: the cap should be solved for rather than scaled -- pick the
    largest open interest whose forced liquidation, at observed depth, keeps
    expected slippage inside the liquidation buffer.
    """
    normalised = min(max(risk_score, 0.0), 100.0) / 100.0
    multiple = BASE_DEPTH_MULTIPLE * (1.0 - DEPTH_MULTIPLE_RISK_SENSITIVITY * normalised)
    return max(market_depth, 0.0) * multiple


def position_limit(cap: float, risk_score: float) -> float:
    """Return the maximum single-account position in USD notional.

    Placeholder implementation: a share of the market-wide cap that falls with
    risk, limiting how much of a thin market one account can represent.

    Future work: concentration should be measured across correlated markets, not
    per market. Several private-company exposures in the same sector and vintage
    are close to one position for liquidation purposes.
    """
    normalised = min(max(risk_score, 0.0), 100.0) / 100.0
    share = max(BASE_ACCOUNT_SHARE * (1.0 - normalised), MIN_ACCOUNT_SHARE)
    return max(cap, 0.0) * share
