"""Data models for the risk engine.

Every value here is synthetic. Scores are unit-free and normalised to [0, 1] so
that a single model can describe both a deeply liquid public asset and an
illiquid private-company exposure. Monetary values are in USD notional.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RiskInputs(BaseModel):
    """The market-state description the engine consumes.

    The normalised scores are all oriented so that **1.0 is the benign end** and
    **0.0 is the hostile end** where that is meaningful (``liquidity_score``,
    ``oracle_confidence``, ``hedgeability_score``), and so that **1.0 is the
    hostile end** for explicit risk measures (``jump_risk``,
    ``event_proximity``).
    """

    model_config = ConfigDict(extra="forbid")

    liquidity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Tradeability of the underlying. 1.0 = continuous deep public market, "
        "0.0 = occasional negotiated private transfers.",
    )
    oracle_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in the reference price feed. 1.0 = many independent "
        "real-time sources, 0.0 = a single unverifiable mark.",
    )
    price_staleness_days: float = Field(
        ...,
        ge=0.0,
        description="Age in days of the most recent observable transaction or mark.",
    )
    oracle_dispersion: float = Field(
        ...,
        ge=0.0,
        description="Relative disagreement across price sources, as a fraction of the "
        "reference price (0.05 = sources differ by ~5%).",
    )
    jump_risk: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Propensity for discontinuous repricing (gap risk). 1.0 = price is "
        "expected to move in large discrete steps rather than continuously.",
    )
    hedgeability_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Ability of a market maker to offset exposure. 1.0 = a liquid "
        "spot/futures hedge exists, 0.0 = no hedge instrument at all.",
    )
    event_proximity: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Nearness of a scheduled repricing event (funding round, tender, "
        "lockup expiry, earnings). 1.0 = imminent.",
    )
    current_open_interest: float = Field(
        ...,
        ge=0.0,
        description="Current market-wide open interest in USD notional.",
    )
    market_depth: float = Field(
        ...,
        ge=0.0,
        description="USD notional absorbable within an acceptable slippage band on the "
        "hedging venue.",
    )


class RiskOutputs(BaseModel):
    """The risk parameters the engine recommends for a market.

    ``score_breakdown`` exposes the per-component penalties that produced
    ``risk_score`` so that a recommendation is always explainable rather than a
    single opaque number.
    """

    model_config = ConfigDict(extra="forbid")

    risk_score: float = Field(
        ..., ge=0.0, le=100.0, description="Composite risk score. 0 = benign, 100 = extreme."
    )
    recommended_max_leverage: float = Field(
        ..., gt=0.0, description="Maximum leverage a position may be opened at, as a multiple."
    )
    initial_margin: float = Field(
        ...,
        gt=0.0,
        le=1.0,
        description="Collateral required to open, as a fraction of position notional.",
    )
    maintenance_margin: float = Field(
        ...,
        gt=0.0,
        le=1.0,
        description="Collateral required to avoid liquidation, as a fraction of notional.",
    )
    position_limit: float = Field(
        ..., ge=0.0, description="Maximum per-account position in USD notional."
    )
    open_interest_cap: float = Field(
        ..., ge=0.0, description="Maximum market-wide open interest in USD notional."
    )
    liquidation_buffer: float = Field(
        ...,
        ge=0.0,
        description="Extra cushion held above maintenance margin, as a fraction of the "
        "maintenance margin requirement.",
    )
    score_breakdown: dict[str, float] = Field(
        default_factory=dict,
        description="Weighted contribution of each risk component to risk_score.",
    )
    engine_version: str = Field(..., description="Version of the parameterisation used.")
