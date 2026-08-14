"use client";

import {
  MECHANISM_LABELS,
  REGIME_LABELS,
  type RegimeTrigger,
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
  tone?: "ok" | "warn" | "danger";
}) {
  return (
    <div className={tone ? `metric metric-${tone}` : "metric"}>
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value}</span>
      {hint ? <span className="metric-hint">{hint}</span> : null}
    </div>
  );
}

function r3DispersionExplanation(
  regime: RegimeTrigger,
  ratio: number,
): string {
  const relative =
    ratio >= 1
      ? `${ratio.toFixed(1)}× larger than`
      : `${(1 / Math.max(ratio, 1e-9)).toFixed(1)}× smaller than`;
  return (
    `Source disagreement is ${relative} one day's expected price move ` +
    `(dispersion ÷ σ√(1/365) = ${ratio.toFixed(2)}). ` +
    `When dispersion dominates diffusion, liquidations track source noise more than ` +
    `solvency — measured buffer ${regime.measured.toFixed(2)} vs cushion ` +
    `${regime.threshold.toFixed(2)}. Raising margin cannot fix that signal.`
  );
}

export default function V1Outputs({ outputs, error, pending }: Props) {
  if (error) {
    return (
      <section className="panel panel-focus">
        <h2>Recommendation</h2>
        <p className="error">{error}</p>
      </section>
    );
  }

  if (!outputs) {
    return (
      <section className="panel panel-focus">
        <h2>Recommendation</h2>
        <p className="control-hint">Evaluating…</p>
      </section>
    );
  }

  const { tradable, margin_diagnostics, size_limits, dimensions } = outputs;
  const viable = outputs.viable_as_continuous_perp;

  return (
    <section className={pending ? "panel panel-focus pending" : "panel panel-focus"}>
      <h2>Recommendation</h2>

      <div className="verdict-banner">
        <div className="verdict-banner-row">
          <div>
            <span className="verdict-kicker">
              {viable
                ? "Inside the viability frontier"
                : "Beyond the viability frontier"}
            </span>
            <p className="verdict-title">
              {MECHANISM_LABELS[outputs.recommended_mechanism]}
            </p>
          </div>
          <span className="verdict-status">
            {viable ? "Continuous margining" : "Mechanism switching"}
          </span>
        </div>
      </div>

      <p className="verdict-body">
        {viable
          ? "Continuous mark-based margining still works here. The response is higher margin, lower leverage, and tighter size limits — not a different instrument."
          : "Continuous mark-based margining cannot be repaired by raising collateral. The recommended instrument is shown above; no tradable leverage is offered below."}
      </p>

      <div className="verdict-stats">
        <div>
          <span className="verdict-stat-label">Viability</span>
          <span className="verdict-stat-value">
            {viable ? "Viable" : "Not viable"}
          </span>
          <span className="verdict-stat-hint">as a continuous perp</span>
        </div>
        <div>
          <span className="verdict-stat-label">Required initial margin</span>
          <span className="verdict-stat-value">
            {percent(margin_diagnostics.required_initial_margin)}
          </span>
          <span className="verdict-stat-hint">Never clamped at 100%</span>
        </div>
        <div>
          <span className="verdict-stat-label">Implied leverage</span>
          <span className="verdict-stat-value">
            {leverage(margin_diagnostics.implied_leverage)}
          </span>
          <span className="verdict-stat-hint">1 / required initial margin</span>
        </div>
      </div>

      {outputs.triggered_regimes.length > 0 ? (
        <>
          <h3>Failure boundaries</h3>
          <div className="regimes">
            {outputs.triggered_regimes.map((regime) => (
              <details
                className="regime regime-failed"
                key={regime.id}
                open={regime.id === "R3"}
              >
                <summary>
                  <span className="regime-id">
                    {REGIME_LABELS[regime.id]}
                    <span className="regime-badge">Triggered</span>
                  </span>
                  <span className="regime-numbers">
                    {regime.measured.toFixed(3)} vs {regime.threshold.toFixed(3)}
                  </span>
                </summary>
                <p>
                  {regime.id === "R3"
                    ? r3DispersionExplanation(
                        regime,
                        dimensions.dispersion_diagnostic_ratio,
                      )
                    : regime.description}
                </p>
              </details>
            ))}
          </div>
        </>
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
          tone={
            margin_diagnostics.required_initial_margin >= 1 ? "danger" : "ok"
          }
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
          label="Dispersion vs one-day move"
          value={`${dimensions.dispersion_diagnostic_ratio.toFixed(2)}×`}
          hint="Source disagreement ÷ σ√(1/365)"
          tone={
            dimensions.dispersion_diagnostic_ratio >= 1 ? "warn" : undefined
          }
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
