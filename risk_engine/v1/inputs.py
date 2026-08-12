"""The v1 market state.

Richer than v0's nine scores: quantities carry units, and the model's largest
driver -- volatility -- is a required input rather than something inferred from a
liquidity proxy (specification L2).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .events import ScheduledEvent


class Interval(BaseModel):
    """A closed interval, used where a point estimate would overstate knowledge."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    low: float
    high: float

    @model_validator(mode="after")
    def _ordered(self) -> Interval:
        if self.high < self.low:
            raise ValueError("interval high must be >= low")
        return self

    @classmethod
    def point(cls, value: float) -> Interval:
        return cls(low=value, high=value)

    @property
    def is_point(self) -> bool:
        return self.low == self.high

    @property
    def midpoint(self) -> float:
        return 0.5 * (self.low + self.high)


class MarketState(BaseModel):
    """Everything the v1 engine needs to know about a market.

    Monetary depths are **USD per day**; horizons are in **calendar days**;
    volatilities are **calendar-annualised**.
    """

    model_config = ConfigDict(extra="forbid")

    # ---- Price process ----------------------------------------------------
    volatility: float = Field(
        ...,
        gt=0.0,
        description="sigma: calendar-annualised return volatility. Required (L2); a "
        "zero-volatility asset is outside the model's domain, and sigma appears in a "
        "denominator in the hedge capacity term.",
    )

    # ---- Depth and impact -------------------------------------------------
    spot_depth: float = Field(
        ..., gt=0.0, description="D_spot: USD per day absorbable at acceptable slippage."
    )
    impact_exponent: float = Field(
        ..., gt=0.0, description="alpha: power-law impact exponent at the reference period."
    )
    impact_coefficient: float = Field(
        ..., gt=0.0, description="gamma: impact at one day of depth, as a fraction."
    )

    # ---- Hedge ------------------------------------------------------------
    hedge_depth: float = Field(
        default=0.0, ge=0.0, description="D_hedge: USD per day in the hedge instrument."
    )
    hedge_volatility: float | None = Field(
        default=None, gt=0.0, description="sigma_h: calendar-annualised."
    )
    hedge_correlation: float | None = Field(
        default=None, ge=-1.0, le=1.0, description="rho_h: correlation to the underlying."
    )
    hedge_ratio: float = Field(
        default=0.0, ge=0.0, le=1.0, description="H: fraction of notional hedged."
    )

    # ---- Price discovery --------------------------------------------------
    mark_staleness_days: float = Field(
        ..., ge=0.0, description="tau_stale: age of the current reference mark."
    )
    mark_refresh_days: float = Field(
        ..., gt=0.0, description="tau_d: expected interval between mark refreshes."
    )
    source_count: int = Field(
        default=1, ge=1, description="n_src: independent external sources behind the mark."
    )
    source_dispersion: float | None = Field(
        default=None,
        ge=0.0,
        description="delta: disagreement across sources. Undefined, and rejected, when "
        "there is only one source.",
    )
    source_correlation: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="rho_src: correlation between sources. At 1.0, extra sources add "
        "nothing.",
    )

    # ---- Jumps ------------------------------------------------------------
    jump_intensity: float = Field(
        ..., ge=0.0, description="lambda: expected jumps beyond the tail scale, per year."
    )
    jump_tail_index: float = Field(
        ..., gt=0.0, description="xi: Pareto tail index in log-return space."
    )
    jump_scale: float = Field(
        ..., gt=0.0, description="m0: tail scale, as a log-return."
    )

    # ---- Positioning ------------------------------------------------------
    open_interest_long: float = Field(default=0.0, ge=0.0, description="USD notional.")
    open_interest_short: float = Field(default=0.0, ge=0.0, description="USD notional.")
    crowding: Interval = Field(
        ...,
        description="phi_1: share of open interest within a 1% move of its liquidation "
        "trigger. No default (L5); supply a point value or an interval.",
    )

    event: ScheduledEvent | None = Field(default=None)

    @model_validator(mode="after")
    def _check_consistency(self) -> MarketState:
        if self.source_count == 1 and self.source_dispersion is not None:
            raise ValueError(
                "source_dispersion is undefined with a single source; omit it and the "
                "engine will substitute the documented prior"
            )
        if self.source_count > 1 and self.source_dispersion is None:
            raise ValueError("source_dispersion is required when source_count > 1")
        if self.hedge_depth > 0.0 and (
            self.hedge_volatility is None or self.hedge_correlation is None
        ):
            raise ValueError(
                "hedge_volatility and hedge_correlation are required when hedge_depth > 0"
            )
        if not 0.0 <= self.crowding.low <= self.crowding.high <= 1.0:
            raise ValueError("crowding (phi_1) must lie within [0, 1]")
        if self.crowding.low <= 0.0:
            raise ValueError("crowding (phi_1) must be strictly positive")
        return self

    @property
    def gross_open_interest(self) -> float:
        return self.open_interest_long + self.open_interest_short

    @property
    def net_open_interest(self) -> float:
        return self.open_interest_long - self.open_interest_short
