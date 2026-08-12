# When Should a Perp Stop Being a Perp?

**PrivatePerp Risk Engine — mapping the viability frontier of continuous
margining for illiquid underlyings.**

**Live Demo:** https://privateperp-risk-engine.vercel.app/

**Model Spec:** [`docs/model_v1_spec.md`](docs/model_v1_spec.md)

**Research prototype · synthetic data only.** Nothing here uses proprietary,
confidential, or internal information. Results are not evidence about any real
market, are not calibrated to empirical data, and are not financial advice. The
contribution is the framework — where continuous mark-based margining ceases to
be viable — not the numerical thresholds on any particular scenario.

## Problem, question, finding

**Problem.** Conventional perpetual futures risk controls assume an observable
reference price, a usable hedge, and a liquid exit. As the underlying moves
toward illiquid private-company exposure, those assumptions break: the mark may
be weeks or months old, no hedge instrument may exist, and closing a position
means moving the market.

**Question.** Can increasingly conservative leverage and margin always
compensate as those assumptions fail? Or, more precisely: under what conditions
does continuous mark-based margining cease to be viable?

**Finding.** No — not always. There is a *viability frontier* beyond which
continuous mark-based margining itself ceases to be the appropriate mechanism.
Past that frontier the honest output is a different instrument (periodic auction
or settled forward), not a perp with a larger number in the margin field.

**Contribution.** The engine can switch from parameter recommendations to
mechanism selection. A risk engine that can only return numbers will always
return one, which is precisely how a venue ends up listing something it should
not have.

The live demo's **Viability Frontier** map shows this as regions in
(staleness × volatility) space for one recorded synthetic illiquid profile. It
is a scenario frontier under stated assumptions, not a universal empirical
boundary.

## The headline finding

One synthetic illiquid market at 90% annualised volatility, held fixed while its
reference mark ages:

| Mark staleness | Required initial margin | Status |
| --- | --- | --- |
| 0d | 70.8% | viable, 1.41x |
| 1d | 74.5% | viable, 1.34x |
| 7d | 110.5% | not viable (R1, R2) — settled forward |
| 120d | 303.0% | not viable (R1, R2, R3) — settled forward |

Margin rises smoothly across the whole range. Viability does not: it stops. Three
independent preconditions fail as the mark ages, and only the first is about the
amount of collateral.

- **R1, solvency.** Required margin passes 100% of notional. Once required
  initial margin exceeds notional, the contract no longer provides meaningful
  leverage and economically approaches a fully collateralized forward. At that
  point, preserving continuous liquidation adds complexity without preserving
  the defining benefit of a perp.
- **R2, observability.** The mark does not refresh even once during an unwind, so
  there is no state feedback while the venue is acting. No collateral schedule
  makes an unobservable state observable.
- **R3, signal-to-noise.** The buffer needed to keep liquidations defensible no
  longer fits between initial and maintenance margin. The liquidation signal can
  become weakly informative about actual solvency.

R2 and R3 are the interesting ones, because raising margin does not address
either. Reproduce the whole frontier with `python -m simulations.viability_frontier`,
which is also where the profile behind these numbers is recorded. Most v1
parameters remain assumptions rather than empirical estimates; two of roughly
thirty are fitted, and both to data this repository invented.

## Running it

Requires Python 3.11+ and Node 20+.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload   # from the repository root
```

```bash
cd frontend && npm install && npm run dev
```

Open `http://localhost:3000`. The frontend expects the API at
`http://127.0.0.1:8000`; override with `NEXT_PUBLIC_API_BASE_URL` in
`frontend/.env.local` (see `.env.local.example`). Interactive API docs are at
`/docs`. The hosted API is on a free tier that sleeps when idle, so the first
load of the live demo may take a moment.

Start with the presets, which walk one engine across four market qualities and
produce four different instruments — perp, perp, periodic auction, settled
forward. The viability frontier at the top of the page shows where continuous
margining ceases to be available as mark staleness and volatility change.

```bash
python -m pytest
python -m ruff check .

python -m simulations.jump_risk
python -m simulations.oracle_staleness
python -m simulations.liquidation_cascade
python -m simulations.viability_frontier
```

## Two engines

`risk_engine/` ships both. v0 is the original composite-score heuristic and still
backs `POST /risk/evaluate` unchanged; v1 backs `POST /risk/v1/evaluate`. Both are
in the UI, side by side, because the comparison is part of the argument.

| | v0 | v1 |
| --- | --- | --- |
| Structure | one composite score drives every output | five risk dimensions mapped separately |
| Volatility | not an input | required, first-class |
| Units | dimensionless scores | USD/day, calendar days, annualised rates |
| Failure mode | always returns a leverage number | can return "no viable parameters" |
| Provenance | untracked | every parameter tagged measured, fitted, or assumed |

v1's full derivation, including the dimensional-consistency argument and every
formula, is in [`docs/model_v1_spec.md`](docs/model_v1_spec.md).

## Layout

```
risk_engine/     Pure Python domain logic. No web framework, no I/O, no config.
  v1/            The five-dimension model: uncertainty, liquidity, jumps, hedging, cascade.
backend/         FastAPI. Validation and transport only.
frontend/        Next.js + TypeScript. Sliders in, parameter cards out. No risk logic.
simulations/     Scripts that stress-test the engine's recommendations.
data/            Synthetic market profiles and depth curves.
```

The rule the layout enforces: **all risk logic lives in `risk_engine/`**, so the
API, the simulations, and any notebook exercise byte-identical code. Details in
[`docs/architecture.md`](docs/architecture.md).

## What the simulations are for

The engine is not fit to data, so the simulations are the only check that its
recommendations are sane. All use calendar time, 365 days per year.

| Simulation | Question it asks |
| --- | --- |
| `jump_risk.py` | Does recommended margin cover the loss distribution when the asset reprices in discrete jumps? |
| `oracle_staleness.py` | Does the liquidation buffer cover the error in a stale mark? |
| `liquidation_cascade.py` | Does the open interest cap stop forced unwinds from becoming self-reinforcing in a thin book? |
| `viability_frontier.py` | Under what conditions does continuous mark-based margining cease to be viable? |

The second is what motivated v1. v0's liquidation buffer barely moves as marks
age — 11.2% at a 7-day refresh, 12.2% at 30 days — while p95 mark error goes from
10.5% to 23.2%. Widening the buffer does not survive contact with the numbers,
so v1 asks a different question instead.

## Roadmap

- Calibrate anything. Two of roughly thirty v1 parameters are fitted, and both to
  data this repository invented.
- Make account crowding observable from venue state, so the open interest cap can
  be a number rather than an order-of-magnitude range.
- Add funding rate as an output; it is a primary risk lever for an underlying
  that cannot be arbitraged.
- Manipulation-resistant blended marks, explicitly deferred from v1.
- Correlation between markets: position limits are per-market today, and several
  private exposures of the same sector and vintage are close to a single position
  for liquidation purposes.

Known limitations, including the ones v1 does not fix, are in
[`docs/assumptions.md`](docs/assumptions.md).

## License

MIT.
