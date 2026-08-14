"use client";

import type { RiskOutputs } from "@/lib/types";

const COMPONENT_LABELS: Record<string, string> = {
  illiquidity: "Illiquidity",
  price_discovery: "Price discovery",
  jump_risk: "Jump risk",
  unhedgeability: "Unhedgeability",
  event_proximity: "Event proximity",
  crowding: "Crowding",
};

const formatUsd = (value: number) =>
  value >= 1_000_000
    ? `$${(value / 1_000_000).toFixed(2)}m`
    : `$${Math.round(value / 1_000).toLocaleString()}k`;

const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`;

function riskBand(score: number): string {
  if (score < 25) return "low";
  if (score < 50) return "moderate";
  if (score < 75) return "high";
  return "extreme";
}

interface Props {
  outputs: RiskOutputs | null;
  error: string | null;
  pending: boolean;
}

export default function OutputCards({ outputs, error, pending }: Props) {
  if (error) {
    return (
      <section className="panel panel-focus">
        <h2>Recommended parameters</h2>
        <p className="error">
          {error} Start the backend with{" "}
          <code>uvicorn backend.app.main:app --reload</code> from the repository
          root.
        </p>
      </section>
    );
  }

  const cards = outputs
    ? [
        {
          label: "Max leverage",
          value: `${outputs.recommended_max_leverage.toFixed(1)}x`,
          note: "Ceiling for new positions",
        },
        {
          label: "Initial margin",
          value: formatPercent(outputs.initial_margin),
          note: "Collateral to open, share of notional",
        },
        {
          label: "Maintenance margin",
          value: formatPercent(outputs.maintenance_margin),
          note: "Collateral to avoid liquidation",
        },
        {
          label: "Liquidation buffer",
          value: formatPercent(outputs.liquidation_buffer),
          note: "Cushion above maintenance margin",
        },
        {
          label: "Position limit",
          value: formatUsd(outputs.position_limit),
          note: "Per-account notional",
        },
        {
          label: "Open interest cap",
          value: formatUsd(outputs.open_interest_cap),
          note: "Market-wide notional",
        },
      ]
    : [];

  return (
    <section className={pending ? "panel panel-focus pending" : "panel panel-focus"}>
      <h2>Recommended parameters</h2>

      {outputs ? (
        <>
          <div className={`score score-${riskBand(outputs.risk_score)}`}>
            <span className="score-value">{outputs.risk_score.toFixed(1)}</span>
            <span className="score-label">
              risk score &middot; {riskBand(outputs.risk_score)}
            </span>
            <div className="score-track">
              <div
                className="score-fill"
                style={{ width: `${outputs.risk_score}%` }}
              />
            </div>
          </div>

          <div className="cards">
            {cards.map((card) => (
              <article className="card" key={card.label}>
                <span className="card-label">{card.label}</span>
                <span className="card-value">{card.value}</span>
                <span className="card-note">{card.note}</span>
              </article>
            ))}
          </div>

          <h3>What drove the score</h3>
          <ul className="breakdown">
            {Object.entries(outputs.score_breakdown)
              .sort(([, a], [, b]) => b - a)
              .map(([key, contribution]) => (
                <li key={key}>
                  <span className="breakdown-label">
                    {COMPONENT_LABELS[key] ?? key}
                  </span>
                  <span className="breakdown-track">
                    <span
                      className="breakdown-fill"
                      style={{ width: `${(contribution / 25) * 100}%` }}
                    />
                  </span>
                  <span className="breakdown-value">
                    {contribution.toFixed(1)}
                  </span>
                </li>
              ))}
          </ul>

          <p className="footnote">
            Placeholder heuristics, engine {outputs.engine_version}. Synthetic
            data only.
          </p>
        </>
      ) : (
        <p className="muted">Evaluating&hellip;</p>
      )}
    </section>
  );
}
