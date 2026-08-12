import type { MarketState } from "./typesV1";

/**
 * Synthetic market profiles spanning the liquidity spectrum.
 *
 * All fabricated. `illiquid_private` is the profile recorded in
 * `simulations/viability_frontier.py`, so the staleness experiment in the UI and
 * the frontier table in the specification are describing the same market.
 */
export interface PresetV1 {
  id: string;
  label: string;
  notes: string;
  state: MarketState;
}

/** The recorded frontier profile, at the 90% volatility the spec headlines. */
export const FRONTIER_PROFILE: MarketState = {
  volatility: 0.9,
  spot_depth: 350_000,
  impact_exponent: 1.15,
  impact_coefficient: 0.0703,
  hedge_depth: 17_500,
  hedge_volatility: 0.6,
  hedge_correlation: 0.22,
  hedge_ratio: 0.05,
  mark_staleness_days: 0,
  mark_refresh_days: 1,
  source_count: 3,
  source_dispersion: 0.05,
  source_correlation: 0.5,
  jump_intensity: 10,
  jump_tail_index: 2,
  jump_scale: 0.05,
  open_interest_long: 5_000_000,
  open_interest_short: 500_000,
  crowding: { low: 0.02, high: 0.2 },
};

export const PRESETS_V1: PresetV1[] = [
  {
    id: "liquid_public",
    label: "Liquid public asset",
    notes:
      "Continuous price discovery, deep hedge, eight loosely correlated sources.",
    state: {
      volatility: 0.35,
      spot_depth: 20_000_000,
      impact_exponent: 0.71,
      impact_coefficient: 0.0077,
      hedge_depth: 19_000_000,
      hedge_volatility: 0.35,
      hedge_correlation: 0.97,
      hedge_ratio: 0.95,
      mark_staleness_days: 0,
      mark_refresh_days: 1,
      source_count: 8,
      source_dispersion: 0.001,
      source_correlation: 0.3,
      jump_intensity: 1,
      jump_tail_index: 3,
      jump_scale: 0.03,
      open_interest_long: 25_000_000,
      open_interest_short: 20_000_000,
      crowding: { low: 0.02, high: 0.1 },
    },
  },
  {
    id: "thin_public",
    label: "Thin public asset",
    notes: "Wide spreads and gappy prints; borrow for hedging is limited.",
    state: {
      volatility: 0.6,
      spot_depth: 900_000,
      impact_exponent: 0.92,
      impact_coefficient: 0.028,
      hedge_depth: 320_000,
      hedge_volatility: 0.5,
      hedge_correlation: 0.6,
      hedge_ratio: 0.35,
      mark_staleness_days: 1,
      mark_refresh_days: 1,
      source_count: 4,
      source_dispersion: 0.01,
      source_correlation: 0.4,
      jump_intensity: 4,
      jump_tail_index: 2.5,
      jump_scale: 0.04,
      open_interest_long: 3_000_000,
      open_interest_short: 1_800_000,
      crowding: { low: 0.02, high: 0.15 },
    },
  },
  {
    id: "late_stage_secondary",
    label: "Late-stage private / secondary",
    notes:
      "Occasional negotiated transfers, marks three weeks apart. Collateral is still affordable — it is the liquidation decision that stops being sound.",
    state: {
      volatility: 0.45,
      spot_depth: 600_000,
      impact_exponent: 1.1,
      impact_coefficient: 0.052,
      hedge_depth: 90_000,
      hedge_volatility: 0.45,
      hedge_correlation: 0.45,
      hedge_ratio: 0.25,
      mark_staleness_days: 21,
      mark_refresh_days: 21,
      source_count: 3,
      source_dispersion: 0.03,
      source_correlation: 0.5,
      jump_intensity: 5,
      jump_tail_index: 2.4,
      jump_scale: 0.045,
      open_interest_long: 4_000_000,
      open_interest_short: 1_000_000,
      crowding: { low: 0.02, high: 0.2 },
    },
  },
  {
    id: "illiquid_private",
    label: "Highly illiquid private",
    notes:
      "Fictional private company. Reprices on funding rounds, effectively no hedge. This is the recorded frontier profile.",
    state: { ...FRONTIER_PROFILE, mark_staleness_days: 120, mark_refresh_days: 120 },
  },
];

export const DEFAULT_PRESET_V1 = PRESETS_V1[2];
