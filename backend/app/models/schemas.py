"""HTTP request and response envelopes.

The domain models live in ``risk_engine.inputs`` and are reused directly so the
API cannot drift from the engine. Only transport-level wrappers belong here.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from risk_engine.inputs import RiskInputs, RiskOutputs
from risk_engine.v1 import MarketState, PolicyParameters, RiskOutputsV1
from risk_engine.v1.regimes import Mechanism, RegimeId


class HealthResponse(BaseModel):
    status: str = Field(..., description="'ok' when the service is able to serve requests.")
    api_version: str
    engine_version: str


class RiskEvaluationRequest(BaseModel):
    """Request body for ``POST /risk/evaluate``."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "inputs": {
                    "liquidity_score": 0.25,
                    "oracle_confidence": 0.45,
                    "price_staleness_days": 45.0,
                    "oracle_dispersion": 0.12,
                    "jump_risk": 0.7,
                    "hedgeability_score": 0.2,
                    "event_proximity": 0.4,
                    "current_open_interest": 5_000_000.0,
                    "market_depth": 750_000.0,
                }
            }
        }
    )

    inputs: RiskInputs


class RiskEvaluationResponse(BaseModel):
    """Response body for ``POST /risk/evaluate``."""

    inputs: RiskInputs
    outputs: RiskOutputs


class RiskEvaluationV1Request(BaseModel):
    """Request body for ``POST /risk/v1/evaluate``.

    ``policy`` is optional; omitting it uses the documented default venue policy.
    Exposing it at all is deliberate — the distinction between what the venue
    chooses and what the market imposes is the point of the model, and a caller
    should be able to see a limit move because they widened their own risk
    appetite rather than because the asset changed.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "state": {
                    "volatility": 0.90,
                    "spot_depth": 350_000.0,
                    "impact_exponent": 1.15,
                    "impact_coefficient": 0.0703,
                    "hedge_depth": 17_500.0,
                    "hedge_volatility": 0.60,
                    "hedge_correlation": 0.22,
                    "hedge_ratio": 0.05,
                    "mark_staleness_days": 30.0,
                    "mark_refresh_days": 30.0,
                    "source_count": 3,
                    "source_dispersion": 0.05,
                    "source_correlation": 0.5,
                    "jump_intensity": 10.0,
                    "jump_tail_index": 2.0,
                    "jump_scale": 0.05,
                    "open_interest_long": 5_000_000.0,
                    "open_interest_short": 500_000.0,
                    "crowding": {"low": 0.02, "high": 0.20},
                }
            }
        }
    )

    state: MarketState
    policy: PolicyParameters | None = None


class RiskEvaluationV1Response(BaseModel):
    """Response body for ``POST /risk/v1/evaluate``.

    Carries the whole v1 output: viability, mechanism, triggered regimes, size
    limits, unclamped margin diagnostics, dimensions, and provenance. Nothing is
    summarised away at the transport layer, because the parts a consumer is most
    likely to skip — the regimes and the provenance — are the parts that say when
    the headline numbers should not be used.
    """

    state: MarketState
    policy: PolicyParameters
    outputs: RiskOutputsV1


class FrontierCellV1(BaseModel):
    """One cell of the viability-frontier map — render data only."""

    volatility: float
    staleness_days: float
    mechanism: Mechanism
    viable: bool
    initial_margin: float
    regimes: list[RegimeId]


class FrontierV1Request(BaseModel):
    """Request body for ``POST /risk/v1/frontier``.

    Sweeps a fixed (staleness × volatility) grid while holding every other field
    of ``state`` constant. Request ``volatility``, ``mark_staleness_days``, and
    ``mark_refresh_days`` are ignored for cell colour: each cell sets
    ``mark_refresh_days = max(staleness, 1)`` to match the frozen research
    convention. The live assessment still uses the full state via
    ``/risk/v1/evaluate``.
    """

    state: MarketState
    policy: PolicyParameters | None = None


class FrontierV1Response(BaseModel):
    """Response body for ``POST /risk/v1/frontier``."""

    staleness_days: list[float]
    volatilities: list[float]
    cells: list[FrontierCellV1]
    evaluations: int
    engine_version: str
