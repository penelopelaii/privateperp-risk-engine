"use client";

import {
  MECHANISM_LABELS,
  REGIME_LABELS,
  type RiskOutputsV1,
} from "@/lib/typesV1";

const percent = (value: number) => `${(value * 100).toFixed(1)}%`;
const leverage = (value: number) => `${value.toFixed(2)}x`;
const usd = (value: number) =>
  value >= 1_000_000
    ? `$${(value / 1_000_000).toFixed(2)}m`
    : `$${(value / 1_000).toFixed(0)}k`;
const usdPerDay = (value: number) => `${usd(value)}/day`;

interface Props {
  outputs: RiskOutputsV1 | null;
  error: string | null;
  pending: boolean;
}

function Metric({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "warn" | "danger";
}) {
  return (
    <div className={tone ? `metric metric-${tone}` : "metric"}>
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value}</span>
      {hint ? <span className="metric-hint">{hint}</span> : null}
    </div>
  );
}

export default function V1Outputs({ outputs, error, pending }: Props) {
  if (error) {
    return (
      <section className="panel">
        <h2>Assessment</h2>
        <p className="error">{error}</p>
      </section>
    );
  }

  if (!outputs) {
    return (
      <section className="panel">
        <h2>Assessment</h2>
        <p className="control-hint">Evaluating…</p>
      </section>
    );
  }

  const { tradable, margin_diagnostics, size_limits, dimensions } = outputs;
  const viable = outputs.viable_as_continuous_perp;

  return (
    <section className={pending ? "panel pending" : "panel"}>
      <h2>Assessment</h2>

      <div className={viable ? "verdict verdict-ok" : "verdict verdict-fail"}>
        <div className="verdict-head">
          <span className="verdict-flag">
            {viable ? "Viable as a continuous perp" : "Not viable as a continuous perp"}
          </span>
          <span className="verdict-mechanism">
            {MECHANISM_LABELS[outputs.recommended_mechanism]}
          </span>
        </div>
        <p className="verdict-body">
          {viable
            ? "All three preconditions hold, so continuous mark-based margining is an admissible mechanism here."
            : "Continuous mark-based margining is not a parameter setting that can be tightened into working. The recommended instrument is shown above; no tradable leverage is offered below."}
        </p>
      </div>

      {outputs.triggered_regimes.length > 0 ? (
        <div className="regimes">
          {outputs.triggered_regimes.map((regime) => (
            <details className="regime" key={regime.id}>
              <summary>
                <span className="regime-id">{REGIME_LABELS[regime.id]}</span>
                <span className="regime-numbers">
                  {regime.measured.toFixed(3)} vs {regime.threshold.toFixed(3)}
                </span>
              </summary>
              <p>{regime.description}</p>
            </details>
          ))}
        </div>
      ) : null}

      <h3>Tradable parameters</h3>
      {tradable ? (
        <div className="metrics">
          <Metric label="Max leverage" value={leverage(tradable.max_leverage)} />
          <Metric label="Initial margin" value={percent(tradable.initial_margin)} />
          <Metric
            label="Maintenance margin"
            value={percent(tradable.maintenance_margin)}
          />
          <Metric
            label="Liquidation buffer"
            value={percent(tradable.liquidation_buffer)}
            hint="Fraction of notional"
          />
        </div>
      ) : (
        <p className="none-note">
          None. Showing the unconstrained requirement as a diagnostic instead — a
          sub-1x figure is not a perp recommendation.
        </p>
      )}

      <h3>Margin diagnostics{tradable ? "" : " (unconstrained)"}</h3>
      <div className="metrics">
        <Metric
          label="Required initial margin"
          value={percent(margin_diagnostics.required_initial_margin)}
          hint="Never clamped at 100%"
          tone={margin_diagnostics.required_initial_margin >= 1 ? "danger" : undefined}
        />
        <Metric
          label="Required maintenance margin"
          value={percent(margin_diagnostics.required_maintenance_margin)}
        />
        <Metric
          label="Implied leverage"
          value={leverage(margin_diagnostics.implied_leverage)}
          hint="1 / required initial margin"
          tone={margin_diagnostics.implied_leverage < 1 ? "warn" : undefined}
        />
        <Metric
          label="Jump-capped leverage"
          value={leverage(margin_diagnostics.jump_capped_leverage)}
          hint="Ceiling from gap risk alone"
        />
      </div>

      <h3>Size limits</h3>
      <div className="metrics">
        <Metric
          label="Position limit"
          value={usd(size_limits.position_limit)}
          hint="Per account"
        />
        <Metric
          label="Open interest cap"
          value={
            size_limits.open_interest_cap_point !== null
              ? usd(size_limits.open_interest_cap_point)
              : `${usd(size_limits.open_interest_cap_low)} – ${usd(size_limits.open_interest_cap_high)}`
          }
          hint={
            size_limits.open_interest_cap_point !== null
              ? "Point value: crowding was supplied as a point"
              : `A range, because account crowding is assumed to lie in ${(size_limits.crowding_low * 100).toFixed(0)}–${(size_limits.crowding_high * 100).toFixed(0)}%`
          }
        />
      </div>

      <h3>Risk dimensions</h3>
      <div className="metrics">
        <Metric
          label="Price uncertainty"
          value={percent(dimensions.price_uncertainty)}
          hint="Standard deviation of the true price around the mark"
        />
        <Metric
          label="Effective depth"
          value={usdPerDay(dimensions.effective_depth)}
          hint="Spot plus whatever the hedge genuinely adds"
        />
        <Metric
          label="Liquidation cost at limit"
          value={percent(dimensions.liquidation_cost_at_limit)}
          hint={`Over a ${dimensions.unwind_days_at_limit.toFixed(1)}-day unwind`}
        />
        <Metric
          label="Residual volatility"
          value={percent(dimensions.residual_volatility)}
          hint="After hedging"
        />
      </div>

      <p className="provenance-note">
        {outputs.contains_assumed_inputs
          ? "Every input in this evaluation is assumed or synthetic. Nothing here is calibrated to a real market."
          : "All inputs measured."}{" "}
        Engine {outputs.engine_version}.
      </p>
    </section>
  );
}
