"""PrivatePerp risk engine, version 1.

Five risk dimensions mapped separately onto six outputs, replacing v0's single
composite score. The structural claim is that the outputs answer different
questions and so should not share a driver: initial margin asks how far the price
can move before the venue can react, maintenance margin asks what getting flat
will cost, and the size limits ask whether the position can be absorbed at all.

The engine may conclude that no parameters work. That is a result, not a failure:
continuous mark-based margining has preconditions, and on a sufficiently stale,
sufficiently illiquid underlying they fail regardless of collateral. See
``docs/model_v1_spec.md``.

v0 is untouched and still reachable through ``risk_engine.evaluate_risk``.
"""

from __future__ import annotations

from . import cascade, events, hedging, jumps, liquidity, uncertainty, units
from .inputs import Interval, MarketState
from .outputs import (
    MarginDiagnostics,
    RiskDimensions,
    RiskOutputsV1,
    SizeLimits,
    TradableParameters,
)
from .params import DEFAULT_POLICY, PolicyParameters
from .provenance import Provenance, contains_assumed_inputs, merge
from .regimes import Mechanism, RegimeId, RegimeTrigger, evaluate_regimes, select_mechanism

ENGINE_VERSION = "1.0.0"

__all__ = [
    "DEFAULT_POLICY",
    "ENGINE_VERSION",
    "Interval",
    "MarketState",
    "Mechanism",
    "PolicyParameters",
    "Provenance",
    "RegimeId",
    "RegimeTrigger",
    "RiskOutputsV1",
    "evaluate_risk_v1",
]


def evaluate_risk_v1(
    state: MarketState,
    params: PolicyParameters | None = None,
    *,
    input_provenance: dict[str, Provenance] | None = None,
) -> RiskOutputsV1:
    """Evaluate a market and return its v1 risk assessment.

    Ordering matters and is not arbitrary. The position limit comes first,
    because it fixes the unwind horizon that maintenance margin is priced over;
    maintenance margin comes next, because initial margin is built on top of it;
    and the regime checks come last, because they compare the two margins.
    """
    params = params or DEFAULT_POLICY

    # --- Event channels, applied before anything consumes the state ---------
    refresh_days = events.effective_refresh_days(state.event, state.mark_refresh_days)
    depth_multiplier = events.depth_multiplier(state.event, params.max_unwind_days)

    # --- Dimensions ---------------------------------------------------------
    sigma_u = uncertainty.price_uncertainty(state, params)
    effective_depth = hedging.effective_depth(state, depth_multiplier)
    residual_vol = hedging.residual_volatility(state)

    q_max = liquidity.position_limit(effective_depth, params)
    tau_u = liquidity.unwind_days(q_max, effective_depth, params)
    cost_at_limit = liquidity.liquidation_cost(q_max, state, effective_depth, params)

    jump_unwind = jumps.jump_loss(state, tau_u, params)
    response_window = params.response_horizon_days + refresh_days
    jump_response = jumps.jump_loss(state, response_window, params)
    jump_refresh = jumps.jump_loss(state, refresh_days, params)
    event_jump = events.unavoidable_jump_loss(state.event, params.response_horizon_days)

    # --- Margins ------------------------------------------------------------
    maintenance = cost_at_limit + params.z_maintenance * sigma_u + jump_unwind
    initial = (
        maintenance
        + params.z_initial * residual_vol * (units.years(response_window)) ** 0.5
        + jump_response
        + event_jump
    )

    jump_capped_leverage = 1.0 / max(jumps.jump_loss(state, params.response_horizon_days, params), 1e-9)
    implied_leverage = 1.0 / initial

    # --- Size limits --------------------------------------------------------
    cap_low, cap_high, cap_point = cascade.open_interest_cap_range(
        effective_depth, state, params
    )
    beta_at_cap = cascade.amplification(
        cascade.open_interest_cap(effective_depth, state, state.crowding.high, params),
        effective_depth,
        state,
        state.crowding.high,
    )

    # --- Regimes ------------------------------------------------------------
    triggered = evaluate_regimes(
        initial_margin=initial,
        maintenance_margin=maintenance,
        refresh_days=refresh_days,
        unwind_days=tau_u,
        price_uncertainty=sigma_u,
        jump_loss_over_refresh=jump_refresh,
        z_spurious=params.z_spurious,
    )
    mechanism = select_mechanism(triggered, refresh_days, params.settlement_horizon_days)
    viable = mechanism is Mechanism.CONTINUOUS_PERP

    tradable = None
    if viable:
        tradable = TradableParameters(
            max_leverage=min(implied_leverage, jump_capped_leverage, params.max_policy_leverage),
            initial_margin=initial,
            maintenance_margin=maintenance,
            liquidation_buffer=params.z_buffer * sigma_u + jump_refresh,
        )

    provenance = merge(params.provenance(), input_provenance or {})

    return RiskOutputsV1(
        viable_as_continuous_perp=viable,
        recommended_mechanism=mechanism,
        triggered_regimes=triggered,
        tradable=tradable,
        margin_diagnostics=MarginDiagnostics(
            required_initial_margin=initial,
            required_maintenance_margin=maintenance,
            implied_leverage=implied_leverage,
            jump_capped_leverage=jump_capped_leverage,
        ),
        size_limits=SizeLimits(
            position_limit=q_max,
            open_interest_cap_low=cap_low,
            open_interest_cap_high=cap_high,
            open_interest_cap_point=cap_point,
            crowding_low=state.crowding.low,
            crowding_high=state.crowding.high,
        ),
        dimensions=RiskDimensions(
            price_uncertainty=sigma_u,
            effective_depth=effective_depth,
            liquidation_cost_at_limit=cost_at_limit,
            unwind_days_at_limit=tau_u,
            jump_loss_response=jump_response,
            jump_loss_unwind=jump_unwind,
            residual_volatility=residual_vol,
            cascade_beta_at_cap=beta_at_cap,
            dispersion_diagnostic_ratio=uncertainty.dispersion_diagnostic_ratio(state, params),
        ),
        contains_assumed_inputs=contains_assumed_inputs(provenance),
        provenance=provenance,
        engine_version=ENGINE_VERSION,
    )
