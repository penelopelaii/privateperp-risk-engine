"use client";

import type { RiskInputs } from "@/lib/types";
import { PRESETS } from "@/lib/presets";

type NumericField = keyof RiskInputs;

interface FieldSpec {
  key: NumericField;
  label: string;
  hint: string;
  min: number;
  max: number;
  step: number;
  format: (value: number) => string;
}

const percent = (value: number) => `${(value * 100).toFixed(0)}%`;
const days = (value: number) => `${value.toFixed(0)}d`;
const basisPoints = (value: number) => `${(value * 100).toFixed(1)}%`;
const usd = (value: number) =>
  value >= 1_000_000
    ? `$${(value / 1_000_000).toFixed(1)}m`
    : `$${(value / 1_000).toFixed(0)}k`;

const MARKET_QUALITY: FieldSpec[] = [
  {
    key: "liquidity_score",
    label: "Liquidity",
    hint: "1.0 = continuous deep market, 0.0 = negotiated private transfers",
    min: 0,
    max: 1,
    step: 0.01,
    format: percent,
  },
  {
    key: "hedgeability_score",
    label: "Hedgeability",
    hint: "Can a market maker offset the exposure at all?",
    min: 0,
    max: 1,
    step: 0.01,
    format: percent,
  },
  {
    key: "jump_risk",
    label: "Jump risk",
    hint: "Propensity to reprice in large discrete steps",
    min: 0,
    max: 1,
    step: 0.01,
    format: percent,
  },
  {
    key: "event_proximity",
    label: "Event proximity",
    hint: "Nearness of a funding round, tender, lockup expiry, or earnings",
    min: 0,
    max: 1,
    step: 0.01,
    format: percent,
  },
];

const PRICE_DISCOVERY: FieldSpec[] = [
  {
    key: "oracle_confidence",
    label: "Oracle confidence",
    hint: "Confidence in the reference price feed",
    min: 0,
    max: 1,
    step: 0.01,
    format: percent,
  },
  {
    key: "price_staleness_days",
    label: "Price staleness",
    hint: "Age of the most recent observable mark",
    min: 0,
    max: 365,
    step: 1,
    format: days,
  },
  {
    key: "oracle_dispersion",
    label: "Oracle dispersion",
    hint: "Disagreement across sources, as a fraction of price",
    min: 0,
    max: 0.3,
    step: 0.005,
    format: basisPoints,
  },
];

const MARKET_SIZE: FieldSpec[] = [
  {
    key: "current_open_interest",
    label: "Current open interest",
    hint: "Market-wide open interest in USD notional",
    min: 0,
    max: 50_000_000,
    step: 250_000,
    format: usd,
  },
  {
    key: "market_depth",
    label: "Market depth",
    hint: "USD notional absorbable within an acceptable slippage band",
    min: 0,
    max: 25_000_000,
    step: 50_000,
    format: usd,
  },
];

interface Props {
  inputs: RiskInputs;
  activePresetId: string | null;
  onChange: (key: NumericField, value: number) => void;
  onPreset: (presetId: string) => void;
}

export default function RiskInputForm({
  inputs,
  activePresetId,
  onChange,
  onPreset,
}: Props) {
  const renderGroup = (title: string, fields: FieldSpec[]) => (
    <fieldset className="group" key={title}>
      <legend>{title}</legend>
      {fields.map((field) => (
        <label className="control" key={field.key}>
          <span className="control-header">
            <span className="control-label">{field.label}</span>
            <span className="control-value">
              {field.format(inputs[field.key])}
            </span>
          </span>
          <input
            type="range"
            min={field.min}
            max={field.max}
            step={field.step}
            value={inputs[field.key]}
            onChange={(event) =>
              onChange(field.key, Number(event.target.value))
            }
          />
          <span className="control-hint">{field.hint}</span>
        </label>
      ))}
    </fieldset>
  );

  return (
    <section className="panel">
      <h2>Market state</h2>

      <div className="presets">
        {PRESETS.map((preset) => (
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

      {renderGroup("Market quality", MARKET_QUALITY)}
      {renderGroup("Price discovery", PRICE_DISCOVERY)}
      {renderGroup("Size", MARKET_SIZE)}
    </section>
  );
}
