import type { RiskInputs } from "./types";

/**
 * Synthetic market profiles spanning the liquidity spectrum, mirroring
 * `data/synthetic/asset_profiles.json`. Illustrative only.
 */
export interface Preset {
  id: string;
  label: string;
  notes: string;
  inputs: RiskInputs;
}

export const PRESETS: Preset[] = [
  {
    id: "liquid_public_perp",
    label: "Liquid public perp",
    notes: "Continuous price discovery, deep hedge, many oracle sources.",
    inputs: {
      liquidity_score: 0.95,
      oracle_confidence: 0.98,
      price_staleness_days: 0,
      oracle_dispersion: 0.001,
      jump_risk: 0.1,
      hedgeability_score: 0.95,
      event_proximity: 0,
      current_open_interest: 25_000_000,
      market_depth: 20_000_000,
    },
  },
  {
    id: "mid_cap_public",
    label: "Mid-cap public",
    notes: "Continuous but thinner; scheduled earnings add event risk.",
    inputs: {
      liquidity_score: 0.7,
      oracle_confidence: 0.9,
      price_staleness_days: 1,
      oracle_dispersion: 0.005,
      jump_risk: 0.35,
      hedgeability_score: 0.65,
      event_proximity: 0.3,
      current_open_interest: 8_000_000,
      market_depth: 4_000_000,
    },
  },
  {
    id: "thin_smallcap",
    label: "Thin small-cap",
    notes: "Wide spreads, gappy prints, limited borrow for hedging.",
    inputs: {
      liquidity_score: 0.4,
      oracle_confidence: 0.7,
      price_staleness_days: 3,
      oracle_dispersion: 0.03,
      jump_risk: 0.55,
      hedgeability_score: 0.35,
      event_proximity: 0.2,
      current_open_interest: 3_000_000,
      market_depth: 900_000,
    },
  },
  {
    id: "late_stage_secondary",
    label: "Late-stage secondary",
    notes: "Occasional negotiated transfers; the mark is weeks old.",
    inputs: {
      liquidity_score: 0.2,
      oracle_confidence: 0.45,
      price_staleness_days: 45,
      oracle_dispersion: 0.12,
      jump_risk: 0.7,
      hedgeability_score: 0.15,
      event_proximity: 0.45,
      current_open_interest: 4_000_000,
      market_depth: 600_000,
    },
  },
  {
    id: "synth_private_a",
    label: "SYNTH-PRIVATE-A",
    notes: "Fictional private company. Reprices on funding rounds; no hedge.",
    inputs: {
      liquidity_score: 0.08,
      oracle_confidence: 0.3,
      price_staleness_days: 120,
      oracle_dispersion: 0.2,
      jump_risk: 0.85,
      hedgeability_score: 0.05,
      event_proximity: 0.65,
      current_open_interest: 5_000_000,
      market_depth: 350_000,
    },
  },
];

export const DEFAULT_PRESET = PRESETS[3];
