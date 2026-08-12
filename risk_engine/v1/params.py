"""Policy parameters and declared modelling assumptions, in one place.

Two kinds of number live here and the distinction matters:

* **Policy** -- levers the venue actually controls (horizons, tolerances, caps).
  These are choices, not estimates, and disagreeing with them is a business
  decision rather than a modelling error.
* **Modelling assumptions** -- quantities the model needs, that nobody has
  measured. These are estimates in form and guesses in substance.

Every value here is ``ASSUMED``. None is calibrated.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field

from .provenance import Provenance, uniform


class PolicyParameters(BaseModel):
    """Venue policy and declared assumptions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    # ---- Horizons (policy) ------------------------------------------------
    response_horizon_days: float = Field(
        default=1.0,
        gt=0.0,
        description="tau_r: time for the venue to act once a position deteriorates.",
    )
    max_unwind_days: float = Field(
        default=5.0,
        gt=0.0,
        description="tau_u_max: longest unwind the venue is willing to be exposed for. "
        "Sets the position limit.",
    )
    participation_rate: float = Field(
        default=0.20,
        gt=0.0,
        le=1.0,
        description="rho_part: share of daily depth a liquidation may consume.",
    )
    settlement_horizon_days: float = Field(
        default=365.0,
        gt=0.0,
        description="Longest interval within which a settled forward must be able to "
        "settle against an observable price. Beyond it, nothing is listable.",
    )

    # ---- Tolerances (policy) ---------------------------------------------
    z_initial: float = Field(
        default=2.0, gt=0.0, description="z_theta: quantile for the initial margin add-on."
    )
    z_maintenance: float = Field(
        default=2.0, gt=0.0, description="z_phi: quantile for liquidation-cost coverage."
    )
    z_buffer: float = Field(
        default=2.0, gt=0.0, description="z_psi: quantile for the liquidation buffer."
    )
    z_spurious: float = Field(
        default=2.0,
        gt=0.0,
        description="z_eps: quantile at which a liquidation must be defensible. The "
        "implied two-sided tolerance is eps_spurious = 2*(1 - Phi(z_eps)).",
    )
    jump_tolerance: float = Field(
        default=0.01,
        gt=0.0,
        lt=1.0,
        description="eps_jump: accepted probability of a gap beyond the margined level.",
    )
    cascade_ceiling: float = Field(
        default=0.5,
        gt=0.0,
        lt=1.0,
        description="beta_max: amplification ceiling. 0.5 means a cascade may at most "
        "double the initiating move.",
    )
    max_policy_leverage: float = Field(
        default=20.0, ge=1.0, description="L_policy: venue-wide leverage ceiling."
    )

    # ---- Modelling assumptions -------------------------------------------
    robust_estimator_penalty: float = Field(
        default=math.pi / 2,
        ge=1.0,
        description="kappa_rob: sampling-variance cost of a median relative to a mean "
        "under normality. The price of manipulation resistance, ~57%.",
    )
    dispersion_prior: float = Field(
        default=0.05,
        gt=0.0,
        description="delta_prior: dispersion assumed when there is only one source and "
        "disagreement is therefore unobservable.",
    )

    def provenance(self) -> dict[str, Provenance]:
        """Every policy parameter is an assumption, and says so."""
        return uniform(type(self).model_fields.keys(), Provenance.ASSUMED)


DEFAULT_POLICY = PolicyParameters()
