"use client";

import { useState } from "react";

import { PRESETS_V1 } from "@/lib/presetsV1";
import type { MarketState } from "@/lib/typesV1";

/**
 * Six inputs drive the story; the rest are real model parameters with synthetic
 * defaults, kept behind Advanced so the primary controls stay legible.
 *
 * Hedge correlation and source dispersion are nullable on the wire but never
 * null here: the form always supplies a hedge venue and at least three sources,
 * which keeps the slider set stable.
 */

interface FieldSpec {
  key: keyof MarketState;
  label: string;
  hint: string;
  min: number;
  max: number;
  step: number;
  format: (value: number) => string;
}

const percent = (value: number) => `${(value * 100).toFixed(0)}%`;
const finePercent = (value: number) => `${(value * 100).toFixed(1)}%`;
const days = (value: number) => `${value.toFixed(0)}d`;
const perYear = (value: number) => `${value.toFixed(1)}/yr`;
const plain = (value: number) => value.toFixed(2);
const usdPerDay = (value: number) =>
  value >= 1_000_000
    ? `$${(value / 1_000_000).toFixed(1)}m/day`
    : `$${(value / 1_000).toFixed(0)}k/day`;
const usd = (value: number) =>
  value >= 1_000_000
    ? `$${(value / 1_000_000).toFixed(1)}m`
    : `$${(value / 1_000).toFixed(0)}k`;

const PRIMARY: FieldSpec[] = [
  {
    key: "volatility",
    label: "Annualised volatility",
    hint: "Calendar-annualised. The model's single largest driver, so v1 requires it rather than inferring it.",
    min: 0.05,
    max: 2,
    step: 0.01,
    format: percent,
  },
  {
    key: "mark_staleness_days",
    label: "Mark staleness",
    hint: "Age of the reference mark the venue liquidates against.",
    min: 0,
    max: 180,
    step: 1,
    format: days,
  },
  {
    key: "source_dispersion",
    label: "Source dispersion",
    hint: "How far independent price sources disagree. Read relative to volatility, not in absolute terms.",
    min: 0,
    max: 0.4,
    step: 0.005,
    format: finePercent,
  },
  {
    key: "spot_depth",
    label: "Market depth",
    hint: "USD absorbable per day at acceptable slippage. A rate, not a stock.",
    min: 50_000,
    max: 25_000_000,
    step: 50_000,
    format: usdPerDay,
  },
  {
    key: "hedge_correlation",
    label: "Hedge correlation",
    hint: "Correlation between the hedge instrument and the underlying. At zero, the hedge adds no exit capacity.",
    min: 0,
    max: 1,
    step: 0.01,
    format: plain,
  },
  {
    key: "jump_intensity",
    label: "Jump intensity",
    hint: "Expected repricing jumps beyond the tail scale, per year.",
    min: 0,
    max: 40,
    step: 0.5,
    format: perYear,
  },
];

const ADVANCED: FieldSpec[] = [
  {
    key: "mark_refresh_days",
    label: "Mark refresh interval",
    hint: "Expected gap between marks. Drives R2 and the initial-margin horizon.",
    min: 1,
    max: 180,
    step: 1,
    format: days,
  },
  {
    key: "source_count",
    label: "Independent sources",
    hint: "Averaging credit is withdrawn when disagreement looks structural.",
    min: 1,
    max: 12,
    step: 1,
    format: (value) => value.toFixed(0),
  },
  {
    key: "source_correlation",
    label: "Source correlation",
    hint: "At 1.0, extra sources are worth nothing.",
    min: 0,
    max: 1,
    step: 0.05,
    format: plain,
  },
  {
    key: "impact_exponent",
    label: "Impact exponent",
    hint: "Power-law market impact. Above 1, cost is convex in size.",
    min: 0.5,
    max: 1.8,
    step: 0.01,
    format: plain,
  },
  {
    key: "impact_coefficient",
    label: "Impact at one day of depth",
    hint: "Fractional price concession for liquidating one day's depth.",
    min: 0.001,
    max: 0.2,
    step: 0.001,
    format: finePercent,
  },
  {
    key: "hedge_depth",
    label: "Hedge depth",
    hint: "USD per day available in the hedge instrument.",
    min: 0,
    max: 25_000_000,
    step: 50_000,
    format: usdPerDay,
  },
  {
    key: "hedge_ratio",
    label: "Hedge ratio",
    hint: "Fraction of notional actually hedged.",
    min: 0,
    max: 1,
    step: 0.01,
    format: percent,
  },
  {
    key: "hedge_volatility",
    label: "Hedge volatility",
    hint: "Annualised volatility of the hedge instrument.",
    min: 0.05,
    max: 2,
    step: 0.01,
    format: percent,
  },
  {
    key: "jump_tail_index",
    label: "Jump tail index",
    hint: "Pareto tail in log-return space. Lower is fatter; at or below 1 the mean is undefined.",
    min: 1.1,
    max: 5,
    step: 0.1,
    format: plain,
  },
  {
    key: "jump_scale",
    label: "Jump tail scale",
    hint: "Log-return size at which the jump tail begins.",
    min: 0.01,
    max: 0.3,
    step: 0.005,
    format: finePercent,
  },
  {
    key: "open_interest_long",
    label: "Open interest, long",
    hint: "Directional: only the shocked side liquidates.",
    min: 0,
    max: 50_000_000,
    step: 250_000,
    format: usd,
  },
  {
    key: "open_interest_short",
    label: "Open interest, short",
    hint: "Net open interest drives residual hedging need, not cascade risk.",
    min: 0,
    max: 50_000_000,
    step: 250_000,
    format: usd,
  },
];

interface Props {
  state: MarketState;
  activePresetId: string | null;
  onChange: (key: keyof MarketState, value: number) => void;
  onPreset: (presetId: string) => void;
}

export default function V1InputForm({
  state,
  activePresetId,
  onChange,
  onPreset,
}: Props) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  const renderField = (field: FieldSpec) => {
    const raw = state[field.key];
    const value = typeof raw === "number" ? raw : 0;
    return (
      <label className="control" key={field.key}>
        <span className="control-header">
          <span className="control-label">{field.label}</span>
          <span className="control-value">{field.format(value)}</span>
        </span>
        <input
          type="range"
          min={field.min}
          max={field.max}
          step={field.step}
          value={value}
          onChange={(event) => onChange(field.key, Number(event.target.value))}
        />
        <span className="control-hint">{field.hint}</span>
      </label>
    );
  };

  return (
    <section className="panel">
      <h2>Market state</h2>

      <div className="presets">
        {PRESETS_V1.map((preset) => (
          <button
            key={preset.id}
            type="button"
            title={preset.notes}
            className={preset.id === activePresetId ? "preset active" : "preset"}
            onClick={() => onPreset(preset.id)}
          >
            {preset.label}
          </button>
        ))}
      </div>

      {activePresetId ? (
        <p className="preset-note">
          {PRESETS_V1.find((preset) => preset.id === activePresetId)?.notes}
        </p>
      ) : null}

      <fieldset className="group">
        <legend>Primary drivers</legend>
        {PRIMARY.map(renderField)}
      </fieldset>

      <button
        type="button"
        className="disclosure"
        aria-expanded={showAdvanced}
        onClick={() => setShowAdvanced((open) => !open)}
      >
        {showAdvanced ? "Hide" : "Show"} advanced inputs ({ADVANCED.length})
      </button>

      {showAdvanced ? (
        <fieldset className="group">
          <legend>Advanced</legend>
          <p className="control-hint advanced-note">
            Every one of these is a real model parameter carrying a synthetic
            default. None is calibrated.
          </p>
          {ADVANCED.map(renderField)}
        </fieldset>
      ) : null}
    </section>
  );
}
