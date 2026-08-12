/**
 * Mirrors the Pydantic models in `risk_engine/v1/`.
 *
 * Kept in sync by hand, as with `types.ts`. The one shape worth reading closely
 * is `tradable`: it is `null` whenever the market cannot support a continuous
 * perp, which forces a consumer to handle non-viability before it can render a
 * leverage number. That is deliberate — a clamped 0.37x could be dropped into a
 * card by accident, whereas `null` cannot.
 */

export interface Interval {
  low: number;
  high: number;
}

export type EventType =
  | "priced_round_disclosed"
  | "priced_round_undisclosed"
  | "down_round_recap"
  | "secondary_tender"
  | "ipo_listing"
  | "lockup_expiry";

export interface ScheduledEvent {
  event_type: EventType;
  days_until: number;
}

export interface MarketState {
  volatility: number;
  spot_depth: number;
  impact_exponent: number;
  impact_coefficient: number;
  hedge_depth: number;
  hedge_volatility: number | null;
  hedge_correlation: number | null;
  hedge_ratio: number;
  mark_staleness_days: number;
  mark_refresh_days: number;
  source_count: number;
  source_dispersion: number | null;
  source_correlation: number;
  jump_intensity: number;
  jump_tail_index: number;
  jump_scale: number;
  open_interest_long: number;
  open_interest_short: number;
  crowding: Interval;
  /** Not surfaced in the UI; present so echoed state round-trips faithfully. */
  event?: ScheduledEvent | null;
}

export type Mechanism =
  | "continuous_perp"
  | "periodic_auction"
  | "settled_forward"
  | "not_listable";

export type RegimeId = "R1" | "R2" | "R3";

export interface RegimeTrigger {
  id: RegimeId;
  description: string;
  measured: number;
  threshold: number;
}

export interface RiskDimensions {
  price_uncertainty: number;
  effective_depth: number;
  liquidation_cost_at_limit: number;
  unwind_days_at_limit: number;
  jump_loss_response: number;
  jump_loss_unwind: number;
  residual_volatility: number;
  cascade_beta_at_cap: number;
  dispersion_diagnostic_ratio: number;
}

export interface MarginDiagnostics {
  required_initial_margin: number;
  required_maintenance_margin: number;
  implied_leverage: number;
  jump_capped_leverage: number;
}

export interface SizeLimits {
  position_limit: number;
  open_interest_cap_low: number;
  open_interest_cap_high: number;
  open_interest_cap_point: number | null;
  crowding_low: number;
  crowding_high: number;
}

export interface TradableParameters {
  max_leverage: number;
  initial_margin: number;
  maintenance_margin: number;
  liquidation_buffer: number;
}

export interface RiskOutputsV1 {
  viable_as_continuous_perp: boolean;
  recommended_mechanism: Mechanism;
  triggered_regimes: RegimeTrigger[];
  /** Null whenever `viable_as_continuous_perp` is false. */
  tradable: TradableParameters | null;
  margin_diagnostics: MarginDiagnostics;
  size_limits: SizeLimits;
  dimensions: RiskDimensions;
  contains_assumed_inputs: boolean;
  provenance: Record<string, string>;
  engine_version: string;
}

export interface RiskEvaluationV1Response {
  state: MarketState;
  policy: Record<string, number>;
  outputs: RiskOutputsV1;
}

export const MECHANISM_LABELS: Record<Mechanism, string> = {
  continuous_perp: "Continuous perp",
  periodic_auction: "Periodic auction",
  settled_forward: "Settled forward",
  not_listable: "Not listable",
};

export const REGIME_LABELS: Record<RegimeId, string> = {
  R1: "R1 · Solvency",
  R2: "R2 · Observability",
  R3: "R3 · Signal-to-noise",
};
