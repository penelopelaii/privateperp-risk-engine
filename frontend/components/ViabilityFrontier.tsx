"use client";

import frontierGrid from "@/lib/frontierGrid.json";
import {
  MECHANISM_LABELS,
  type Mechanism,
  type MarketState,
  type RiskOutputsV1,
} from "@/lib/typesV1";

/**
 * The viability frontier for the recorded synthetic illiquid profile, swept over
 * mark staleness and annualised volatility. Cells are baked from the same
 * profile as `simulations/viability_frontier.py` so the map and the published
 * tables describe one evaluation.
 *
 * "You are here" tracks the console's current volatility and staleness on that
 * scenario map. Other inputs (depth, dispersion, hedges) still drive the live
 * assessment panel; the map itself holds the recorded scenario fixed.
 */

const MECHANISM_TONE: Record<Mechanism, string> = {
  continuous_perp: "#3fb984",
  periodic_auction: "#d7b64a",
  settled_forward: "#e08a4b",
  not_listable: "#e0574b",
};

const W = 760;
const H = 320;
const PAD = { left: 58, right: 22, top: 22, bottom: 48 };

const STALENESS = frontierGrid.staleness_days;
const VOLATILITIES = frontierGrid.volatilities;
const MIN_DAYS = STALENESS[0];
const MAX_DAYS = STALENESS[STALENESS.length - 1];
const MIN_VOL = VOLATILITIES[0];
const MAX_VOL = VOLATILITIES[VOLATILITIES.length - 1];

interface Cell {
  volatility: number;
  staleness_days: number;
  mechanism: Mechanism;
  viable: boolean;
  initial_margin: number;
  regimes: string[];
}

const CELLS = frontierGrid.cells as Cell[];

function nearestCell(staleness: number, volatility: number): Cell {
  let best = CELLS[0];
  let bestDist = Number.POSITIVE_INFINITY;
  for (const cell of CELLS) {
    const dist =
      Math.abs(cell.staleness_days - staleness) / MAX_DAYS +
      Math.abs(cell.volatility - volatility) / MAX_VOL;
    if (dist < bestDist) {
      best = cell;
      bestDist = dist;
    }
  }
  return best;
}

function isContinuous(mechanism: Mechanism): boolean {
  return mechanism === "continuous_perp";
}

/**
 * Stepped outline of the continuous-perp region, derived from adjacent-cell
 * transitions in the baked regime grid. Not a fitted curve.
 */
function buildFrontierBoundary(
  dayEdges: { day: number; x0: number; x1: number }[],
  volEdges: { vol: number; y0: number; y1: number }[],
): { path: string; labelX: number; labelY: number } | null {
  const mechanismAt = new Map<string, Mechanism>();
  for (const cell of CELLS) {
    mechanismAt.set(`${cell.volatility}|${cell.staleness_days}`, cell.mechanism);
  }

  const segments: string[] = [];
  // Prefer labeling next to the staleness-direction (vertical) transitions —
  // that is the frontier a reviewer reads left-to-right.
  let labelX = 0;
  let labelY = 0;
  let labelWeight = 0;

  const pushVertical = (x: number, y0: number, y1: number) => {
    const top = Math.min(y0, y1);
    const bottom = Math.max(y0, y1);
    segments.push(`M ${x.toFixed(1)} ${top.toFixed(1)} L ${x.toFixed(1)} ${bottom.toFixed(1)}`);
    labelX += x;
    labelY += (top + bottom) / 2;
    labelWeight += 1;
  };

  const pushHorizontal = (y: number, x0: number, x1: number) => {
    const left = Math.min(x0, x1);
    const right = Math.max(x0, x1);
    segments.push(
      `M ${left.toFixed(1)} ${y.toFixed(1)} L ${right.toFixed(1)} ${y.toFixed(1)}`,
    );
  };

  for (let vi = 0; vi < VOLATILITIES.length; vi++) {
    for (let di = 0; di < STALENESS.length; di++) {
      const here = isContinuous(
        mechanismAt.get(`${VOLATILITIES[vi]}|${STALENESS[di]}`)!,
      );
      if (!here) continue;

      const dayEdge = dayEdges[di];
      const volEdge = volEdges[vi];

      // Right: continuous → non-continuous along staleness.
      if (di < STALENESS.length - 1) {
        const right = isContinuous(
          mechanismAt.get(`${VOLATILITIES[vi]}|${STALENESS[di + 1]}`)!,
        );
        if (!right) pushVertical(dayEdge.x1, volEdge.y0, volEdge.y1);
      }

      // Left: non-continuous → continuous along staleness.
      if (di > 0) {
        const left = isContinuous(
          mechanismAt.get(`${VOLATILITIES[vi]}|${STALENESS[di - 1]}`)!,
        );
        if (!left) pushVertical(dayEdge.x0, volEdge.y0, volEdge.y1);
      }

      // Top: continuous → non-continuous toward higher volatility.
      if (vi < VOLATILITIES.length - 1) {
        const above = isContinuous(
          mechanismAt.get(`${VOLATILITIES[vi + 1]}|${STALENESS[di]}`)!,
        );
        if (!above) pushHorizontal(volEdge.y0, dayEdge.x0, dayEdge.x1);
      }

      // Bottom: non-continuous → continuous toward lower volatility.
      if (vi > 0) {
        const below = isContinuous(
          mechanismAt.get(`${VOLATILITIES[vi - 1]}|${STALENESS[di]}`)!,
        );
        if (!below) pushHorizontal(volEdge.y1, dayEdge.x0, dayEdge.x1);
      }
    }
  }

  if (segments.length === 0 || labelWeight === 0) return null;

  return {
    path: segments.join(" "),
    labelX: Math.min(labelX / labelWeight + 14, W - PAD.right - 8),
    labelY: labelY / labelWeight,
  };
}

interface Props {
  state: MarketState;
  outputs: RiskOutputsV1 | null;
}

export default function ViabilityFrontier({ state, outputs }: Props) {
  const xScale = (days: number) =>
    PAD.left +
    ((days - MIN_DAYS) / (MAX_DAYS - MIN_DAYS)) * (W - PAD.left - PAD.right);
  const yScale = (vol: number) =>
    H -
    PAD.bottom -
    ((vol - MIN_VOL) / (MAX_VOL - MIN_VOL)) * (H - PAD.top - PAD.bottom);

  const dayEdges = STALENESS.map((day, index) => {
    const prev = index === 0 ? day : (STALENESS[index - 1] + day) / 2;
    const next =
      index === STALENESS.length - 1
        ? day
        : (day + STALENESS[index + 1]) / 2;
    return { day, x0: xScale(prev), x1: xScale(next) };
  });
  // Fix endpoints to the plot bounds.
  dayEdges[0].x0 = PAD.left;
  dayEdges[dayEdges.length - 1].x1 = W - PAD.right;

  const volEdges = VOLATILITIES.map((vol, index) => {
    const prev = index === 0 ? vol : (VOLATILITIES[index - 1] + vol) / 2;
    const next =
      index === VOLATILITIES.length - 1
        ? vol
        : (vol + VOLATILITIES[index + 1]) / 2;
    return { vol, y0: yScale(next), y1: yScale(prev) };
  });
  volEdges[0].y1 = H - PAD.bottom;
  volEdges[volEdges.length - 1].y0 = PAD.top;

  const markerX = xScale(
    Math.min(MAX_DAYS, Math.max(MIN_DAYS, state.mark_staleness_days)),
  );
  const markerY = yScale(
    Math.min(MAX_VOL, Math.max(MIN_VOL, state.volatility)),
  );
  const near = nearestCell(state.mark_staleness_days, state.volatility);

  const liveMechanism = outputs?.recommended_mechanism ?? near.mechanism;
  const liveViable = outputs?.viable_as_continuous_perp ?? near.viable;
  const liveIM =
    outputs?.margin_diagnostics.required_initial_margin ?? near.initial_margin;

  const frontier = buildFrontierBoundary(dayEdges, volEdges);

  return (
    <section className="panel experiment frontier">
      <div className="frontier-header">
        <h2>The Viability Frontier</h2>
        <span className="frontier-tag">
          Scenario frontier · synthetic assumptions
        </span>
      </div>

      <p className="experiment-intro">
        Continuous mark-based margining is not a dial you turn. It is a region
        in (staleness, volatility) space. Inside it, risk parameters should
        tighten. Outside it, the market mechanism itself should change.
      </p>

      <svg
        className="chart"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label="Viability frontier: recommended mechanism by mark staleness and annualised volatility"
      >
        {CELLS.map((cell) => {
          const dayEdge = dayEdges.find((edge) => edge.day === cell.staleness_days);
          const volEdge = volEdges.find((edge) => edge.vol === cell.volatility);
          if (!dayEdge || !volEdge) return null;
          return (
            <rect
              key={`${cell.staleness_days}-${cell.volatility}`}
              x={dayEdge.x0}
              y={volEdge.y0}
              width={Math.max(dayEdge.x1 - dayEdge.x0, 0.5)}
              height={Math.max(volEdge.y1 - volEdge.y0, 0.5)}
              fill={MECHANISM_TONE[cell.mechanism]}
              opacity={0.88}
            />
          );
        })}

        {/* Axes */}
        <line
          x1={PAD.left}
          x2={W - PAD.right}
          y1={H - PAD.bottom}
          y2={H - PAD.bottom}
          className="grid-line"
        />
        <line
          x1={PAD.left}
          x2={PAD.left}
          y1={PAD.top}
          y2={H - PAD.bottom}
          className="grid-line"
        />

        {[0, 30, 60, 90, 120].map((tick) => (
          <text
            key={`x-${tick}`}
            x={xScale(tick)}
            y={H - 14}
            className="axis-label"
            textAnchor="middle"
          >
            {tick}d
          </text>
        ))}
        <text
          x={(PAD.left + W - PAD.right) / 2}
          y={H - 2}
          className="axis-title"
          textAnchor="middle"
        >
          Mark staleness
        </text>

        {[0.3, 0.5, 0.7, 0.9, 1.1].map((tick) => (
          <text
            key={`y-${tick}`}
            x={PAD.left - 10}
            y={yScale(tick) + 4}
            className="axis-label"
            textAnchor="end"
          >
            {(tick * 100).toFixed(0)}%
          </text>
        ))}
        <text
          x={14}
          y={(PAD.top + H - PAD.bottom) / 2}
          className="axis-title"
          textAnchor="middle"
          transform={`rotate(-90 14 ${(PAD.top + H - PAD.bottom) / 2})`}
        >
          Annualised volatility
        </text>

        {/* Continuous-perp viability frontier: stepped cell transitions */}
        {frontier ? (
          <g className="frontier-boundary">
            <path d={frontier.path} className="frontier-boundary-line" />
            <text
              x={frontier.labelX}
              y={frontier.labelY}
              className="frontier-boundary-label"
            >
              Continuous-perp viability frontier
            </text>
          </g>
        ) : null}

        {/* You are here */}
        <circle
          cx={markerX}
          cy={markerY}
          r={7}
          className="you-are-here-ring"
        />
        <circle cx={markerX} cy={markerY} r={3.5} className="you-are-here" />
        <text
          x={markerX + 10}
          y={markerY - 10}
          className="you-are-here-label"
        >
          You are here
        </text>
      </svg>

      <div className="legend">
        {(
          [
            "continuous_perp",
            "periodic_auction",
            "settled_forward",
            "not_listable",
          ] as Mechanism[]
        ).map((mechanism) => (
          <span className="legend-item" key={mechanism}>
            <i
              className="swatch"
              style={{ background: MECHANISM_TONE[mechanism] }}
            />{" "}
            {MECHANISM_LABELS[mechanism]}
          </span>
        ))}
        <span className="legend-item">
          <i className="swatch swatch-frontier" /> Continuous-perp viability
          frontier
        </span>
      </div>

      <div className="frontier-contrast">
        <div className="contrast-card">
          <span className="contrast-kicker">Inside the frontier</span>
          <strong>Risk parameters should tighten</strong>
          <p>
            Raise margin, cut leverage, shrink size limits. Continuous
            mark-based margining still works.
          </p>
        </div>
        <div className="contrast-card contrast-card-shift">
          <span className="contrast-kicker">Beyond the frontier</span>
          <strong>The market mechanism itself should change</strong>
          <p>
            No leverage number is admissible. Prefer a periodic auction or a
            settled forward — not a perp with a bigger margin field.
          </p>
        </div>
      </div>

      <div className="experiment-readout">
        <div className={liveViable ? "metric metric-ok" : "metric metric-danger"}>
          <span className="metric-label">At your inputs</span>
          <span className="metric-value">
            {MECHANISM_LABELS[liveMechanism]}
          </span>
          <span className="metric-hint">
            {state.volatility * 100}% vol · {state.mark_staleness_days.toFixed(0)}d
            stale
          </span>
        </div>
        <div className="metric">
          <span className="metric-label">Required initial margin</span>
          <span className="metric-value">{(liveIM * 100).toFixed(1)}%</span>
          <span className="metric-hint">
            {liveViable
              ? "Parameters can still be set"
              : "Unconstrained diagnostic — not a tradable recommendation"}
          </span>
        </div>
        <div className="metric">
          <span className="metric-label">Nearest scenario cell</span>
          <span className="metric-value">
            {MECHANISM_LABELS[near.mechanism]}
          </span>
          <span className="metric-hint">
            Map holds the recorded illiquid profile fixed
          </span>
        </div>
      </div>

      <blockquote className="research-insight">
        Margin can absorb losses, but it cannot repair an unreliable liquidation
        signal. Beyond the viability frontier, the problem shifts from parameter
        calibration to market design.
      </blockquote>

      <p className="provenance-note">
        Scenario map for the recorded synthetic illiquid profile in{" "}
        <code>simulations/viability_frontier.py</code> (5% source dispersion).
        Not an empirical estimate. Reproduce the published tables with{" "}
        <code>python -m simulations.viability_frontier</code>.
      </p>
    </section>
  );
}
