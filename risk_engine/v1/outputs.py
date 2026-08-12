"""The v1 output schema.

Designed so that non-viability is representable without clamping. Two properties
carry the design:

* The unconstrained margin requirement is **always** reported, even at 303% of
  notional. Hiding it would conceal the finding.
* ``tradable`` is ``None`` whenever the market cannot support a continuous perp,
  so a consumer that wants a leverage number must first handle the viability
  case. A clamped 0.37x could be rendered in a card by accident; ``None`` cannot.

The v0 ``RiskOutputs`` is untouched.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .provenance import Provenance
from .regimes import Mechanism, RegimeTrigger


class RiskDimensions(BaseModel):
    """Intermediate quantities, always populated and independent of viability."""

    model_config = ConfigDict(extra="forbid")

    price_uncertainty: float = Field(..., ge=0.0, description="sigma_U, return sigma.")
    effective_depth: float = Field(..., ge=0.0, description="D_eff, USD per day.")
    liquidation_cost_at_limit: float = Field(
        ..., ge=0.0, description="C(q_max), fraction of notional."
    )
    unwind_days_at_limit: float = Field(..., ge=0.0, description="tau_u at the position limit.")
    jump_loss_response: float = Field(
        ..., ge=0.0, description="Jump loss over the response plus refresh horizon."
    )
    jump_loss_unwind: float = Field(..., ge=0.0, description="Jump loss over the unwind.")
    residual_volatility: float = Field(..., ge=0.0, description="After hedging.")
    cascade_beta_at_cap: float = Field(
        ..., ge=0.0, description="Amplification at the recommended cap. Should equal beta_max."
    )
    dispersion_diagnostic_ratio: float = Field(
        ..., ge=0.0, description="Source disagreement over diffusion since the mark."
    )


class MarginDiagnostics(BaseModel):
    """Unconstrained requirements. Deliberately not clamped to 1.0."""

    model_config = ConfigDict(extra="forbid")

    required_initial_margin: float = Field(..., ge=0.0)
    required_maintenance_margin: float = Field(..., ge=0.0)
    implied_leverage: float = Field(
        ..., gt=0.0, description="1 / required initial margin. May be below 1; diagnostic only."
    )
    jump_capped_leverage: float = Field(
        ..., gt=0.0, description="Leverage ceiling implied by gap risk alone."
    )


class SizeLimits(BaseModel):
    """Valid regardless of margining mechanism; an auction needs limits too."""

    model_config = ConfigDict(extra="forbid")

    position_limit: float = Field(..., ge=0.0, description="Per account, USD notional.")
    open_interest_cap_low: float = Field(..., ge=0.0)
    open_interest_cap_high: float = Field(..., ge=0.0)
    open_interest_cap_point: float | None = Field(
        default=None, description="Populated only when phi_1 was supplied as a point value."
    )
    crowding_low: float = Field(..., gt=0.0)
    crowding_high: float = Field(..., gt=0.0)


class TradableParameters(BaseModel):
    """Populated only when the market supports a continuous perp."""

    model_config = ConfigDict(extra="forbid")

    max_leverage: float = Field(..., ge=1.0)
    initial_margin: float = Field(..., gt=0.0, le=1.0)
    maintenance_margin: float = Field(..., gt=0.0, le=1.0)
    liquidation_buffer: float = Field(..., ge=0.0, description="Fraction of notional.")


class RiskOutputsV1(BaseModel):
    """A v1 evaluation."""

    model_config = ConfigDict(extra="forbid")

    viable_as_continuous_perp: bool
    recommended_mechanism: Mechanism
    triggered_regimes: list[RegimeTrigger] = Field(default_factory=list)

    tradable: TradableParameters | None = Field(
        default=None, description="None whenever viable_as_continuous_perp is false."
    )
    margin_diagnostics: MarginDiagnostics
    size_limits: SizeLimits
    dimensions: RiskDimensions

    contains_assumed_inputs: bool
    provenance: dict[str, Provenance] = Field(default_factory=dict)
    engine_version: str
