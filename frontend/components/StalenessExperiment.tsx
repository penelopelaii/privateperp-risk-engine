"use client";

import { useEffect, useMemo, useState } from "react";

import { evaluateRiskV1, sweepStaleness } from "@/lib/api";
import { FRONTIER_PROFILE } from "@/lib/presetsV1";
import {
  MECHANISM_LABELS,
  type Mechanism,
  type RegimeId,
  type RiskOutputsV1,
} from "@/lib/typesV1";

/**
 * The experiment the project exists to show: hold one illiquid market fixed,
 * age its mark, and watch continuous margining stop being an available
 * mechanism rather than merely getting expensive.
 *
 * The profile is the one recorded in `simulations/viability_frontier.py`, so
 * what the browser draws and what the specification tabulates are the same
 * evaluation.
 *
 * Sampling is dense over the first three weeks, where all three preconditions
 * fail, and sparse afterwards, where nothing changes qualitatively. That keeps
 * the one-time sweep to 41 requests while resolving every regime boundary to
 * the day.
 */

const GRID: number[] = [
  ...Array.from({ length: 21 }, (_, index) => index),
  ...Array.from({ length: 20 }, (_, index) => 25 + index * 5),
];

const MAX_DAYS = 120;
const DEBOUNCE_MS = 120;

const MECHANISM_TONE: Record<Mechanism, string> = {
  continuous_perp: "var(--low)",
  periodic_auction: "var(--moderate)",
  settled_forward: "var(--high)",
  not_listable: "var(--extreme)",
};

const W = 760;
const H = 250;
const PAD = { left: 54, right: 18, top: 18, bottom: 46 };

interface SweepPoint {
  days: number;
  initialMargin: number;
  maintenanceMargin: number;
  priceUncertainty: number;
  mechanism: Mechanism;
  viable: boolean;
}

const percent = (value: number) => `${(value * 100).toFixed(1)}%`;

export default function StalenessExperiment() {
  const [staleness, setStaleness] = useState(0);
  const [sweep, setSweep] = useState<SweepPoint[]>([]);
  const [live, setLive] = useState<RiskOutputsV1 | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    sweepStaleness(FRONTIER_PROFILE, GRID, controller.signal)
      .then((responses) =>
        setSweep(
          responses.map((response, index) => ({
            days: GRID[index],
            initialMargin: response.outputs.margin_diagnostics.required_initial_margin,
            maintenanceMargin:
              response.outputs.margin_diagnostics.required_maintenance_margin,
            priceUncertainty: response.outputs.dimensions.price_uncertainty,
            mechanism: response.outputs.recommended_mechanism,
            viable: response.outputs.viable_as_continuous_perp,
          })),
        ),
      )
      .catch(() => {
        if (!controller.signal.aborted) {
          setError("Could not reach the risk engine API.");
        }
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      evaluateRiskV1(
        {
          ...FRONTIER_PROFILE,
          mark_staleness_days: staleness,
          mark_refresh_days: Math.max(staleness, 1),
        },
        controller.signal,
      )
        .then((response) => {
          setLive(response.outputs);
          setError(null);
        })
        .catch(() => {
          if (!controller.signal.aborted) {
            setError("Could not reach the risk engine API.");
          }
        });
    }, DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [staleness]);

  const yMax = useMemo(() => {
    const peak = sweep.reduce((max, point) => Math.max(max, point.initialMargin), 1.2);
    return Math.ceil(peak * 10) / 10;
  }, [sweep]);

  const xScale = (days: number) =>
    PAD.left + (days / MAX_DAYS) * (W - PAD.left - PAD.right);
  const yScale = (value: number) =>
    H - PAD.bottom - (value / yMax) * (H - PAD.top - PAD.bottom);

  const inRange = sweep.filter((point) => point.days <= MAX_DAYS);
  const path = (pick: (point: SweepPoint) => number) =>
    inRange
      .map(
        (point, index) =>
          `${index === 0 ? "M" : "L"} ${xScale(point.days).toFixed(1)} ${yScale(pick(point)).toFixed(1)}`,
      )
      .join(" ");

  const firstNonViable = inRange.find((point) => !point.viable);
  const triggered = new Set<RegimeId>(
    (live?.triggered_regimes ?? []).map((regime) => regime.id),
  );

  return (
    <section className="panel experiment">
      <h2>Experiment · ageing the mark</h2>
      <p className="experiment-intro">
        One illiquid synthetic market at 90% annualised volatility, held fixed
        while its reference mark ages. Margin rises smoothly the whole way. The
        mechanism does not: it stops being available.
      </p>

      {error ? <p className="error">{error}</p> : null}

      <svg
        className="chart"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label="Required margin against mark staleness"
      >
        {[0, 1, 2, 3].map((tick) =>
          tick <= yMax ? (
            <g key={tick}>
              <line
                x1={PAD.left}
                x2={W - PAD.right}
                y1={yScale(tick)}
                y2={yScale(tick)}
                className={tick === 1 ? "grid-line grid-line-notional" : "grid-line"}
              />
              <text x={PAD.left - 10} y={yScale(tick) + 4} className="axis-label">
                {tick * 100}%
              </text>
            </g>
          ) : null,
        )}

        <text
          x={W - PAD.right}
          y={yScale(1) - 8}
          className="axis-note"
          textAnchor="end"
        >
          100% of notional — above this it is not a perp
        </text>

        {firstNonViable ? (
          <rect
            x={xScale(firstNonViable.days)}
            y={PAD.top}
            width={W - PAD.right - xScale(firstNonViable.days)}
            height={H - PAD.top - PAD.bottom}
            className="non-viable-band"
          />
        ) : null}

        <path d={path((point) => point.maintenanceMargin)} className="series series-mm" />
        <path d={path((point) => point.initialMargin)} className="series series-im" />

        {inRange.slice(0, -1).map((point, index) => (
          <rect
            key={point.days}
            x={xScale(point.days)}
            y={H - PAD.bottom + 10}
            width={xScale(inRange[index + 1].days) - xScale(point.days) + 0.5}
            height={7}
            fill={MECHANISM_TONE[point.mechanism]}
          />
        ))}

        <line
          x1={xScale(staleness)}
          x2={xScale(staleness)}
          y1={PAD.top}
          y2={H - PAD.bottom + 19}
          className="marker"
        />

        {[0, 30, 60, 90, 120].map((tick) => (
          <text
            key={tick}
            x={xScale(tick)}
            y={H - 6}
            className="axis-label"
            textAnchor="middle"
          >
            {tick}d
          </text>
        ))}
      </svg>

      <div className="legend">
        <span className="legend-item">
          <i className="swatch swatch-im" /> Required initial margin
        </span>
        <span className="legend-item">
          <i className="swatch swatch-mm" /> Required maintenance margin
        </span>
        <span className="legend-item">
          <i className="swatch" style={{ background: MECHANISM_TONE.continuous_perp }} />{" "}
          Perp
        </span>
        <span className="legend-item">
          <i className="swatch" style={{ background: MECHANISM_TONE.periodic_auction }} />{" "}
          Auction
        </span>
        <span className="legend-item">
          <i className="swatch" style={{ background: MECHANISM_TONE.settled_forward }} />{" "}
          Settled forward
        </span>
      </div>

      <label className="control experiment-slider">
        <span className="control-header">
          <span className="control-label">Mark staleness</span>
          <span className="control-value">{staleness}d</span>
        </span>
        <input
          type="range"
          min={0}
          max={MAX_DAYS}
          step={1}
          value={staleness}
          onChange={(event) => setStaleness(Number(event.target.value))}
        />
      </label>

      {live ? (
        <>
          <div className="experiment-readout">
            <div className="metric">
              <span className="metric-label">Price uncertainty</span>
              <span className="metric-value">
                {percent(live.dimensions.price_uncertainty)}
              </span>
            </div>
            <div className="metric">
              <span className="metric-label">Initial margin</span>
              <span className="metric-value">
                {percent(live.margin_diagnostics.required_initial_margin)}
              </span>
            </div>
            <div className="metric">
              <span className="metric-label">Maintenance margin</span>
              <span className="metric-value">
                {percent(live.margin_diagnostics.required_maintenance_margin)}
              </span>
            </div>
            <div className={live.tradable ? "metric" : "metric metric-danger"}>
              <span className="metric-label">Max leverage</span>
              <span className="metric-value">
                {live.tradable ? `${live.tradable.max_leverage.toFixed(2)}x` : "None"}
              </span>
              {live.tradable ? null : (
                <span className="metric-hint">No admissible leverage</span>
              )}
            </div>
            <div
              className={
                live.viable_as_continuous_perp ? "metric metric-ok" : "metric metric-danger"
              }
            >
              <span className="metric-label">Mechanism</span>
              <span className="metric-value">
                {MECHANISM_LABELS[live.recommended_mechanism]}
              </span>
            </div>
          </div>

          <div className="regime-chips">
            {(["R1", "R2", "R3"] as RegimeId[]).map((id) => (
              <span
                key={id}
                className={triggered.has(id) ? "chip chip-on" : "chip"}
                title={
                  live.triggered_regimes.find((regime) => regime.id === id)
                    ?.description ?? "Precondition holds."
                }
              >
                {id}
                <em>
                  {id === "R1"
                    ? "solvency"
                    : id === "R2"
                      ? "observability"
                      : "signal-to-noise"}
                </em>
              </span>
            ))}
          </div>
        </>
      ) : null}

      <p className="provenance-note">
        Synthetic profile, recorded in{" "}
        <code>simulations/viability_frontier.py</code>. Reproduce the same numbers
        with <code>python -m simulations.viability_frontier</code>.
      </p>
    </section>
  );
}
