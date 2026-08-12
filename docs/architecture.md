# Architecture

## Data flow

```
                 +---------------------------------+
                 |  Next.js frontend               |
                 |  V1 console  |  V0 explorer     |
                 +--------+------------+-----------+
     POST /risk/v1/evaluate|            | POST /risk/evaluate
                           v            v
                 +---------------------------------+
                 |  FastAPI backend                |
                 |  api -> services                |
                 +--------+------------+-----------+
   evaluate_risk_v1(state) |            | evaluate_risk(RiskInputs)
                           v            v
+--------------------------------------------------------------+
|  risk_engine  (pure Python, no I/O, no framework)              |
|                                                                |
|  v1/                              v0                           |
|   uncertainty ---\                 oracle -> risk_score        |
|   liquidity ------\                              |             |
|   jumps -----------> regimes -> outputs          +-> margin    |
|   hedging --------/    (R1/R2/R3, mechanism)     +-> leverage  |
|   cascade -------/                               +-> oi/limits |
|                                                  +-> buffer    |
|                        v0_adapter: RiskInputs -> MarketState   |
+--------------------------------------------------------------+
                             ^
                             | same entry points
                 +-----------+---------------+
                 |  simulations/  notebooks/ |
                 +---------------------------+
```

## The one rule

**All risk logic lives in `risk_engine/` and nothing in `risk_engine/` imports a
web framework, touches the filesystem, or reads configuration.**

Everything else follows from that. It is what lets a simulation, a notebook, and
the API exercise byte-identical logic, and it means the interesting code can be
reviewed without knowing anything about FastAPI.

## Modules

### `risk_engine/`

| File | Responsibility |
| --- | --- |
| `inputs.py` | `RiskInputs` and `RiskOutputs` Pydantic models, with units and ranges declared on every field |
| `oracle.py` | Collapses confidence, staleness, and dispersion into one price-discovery reliability score |
| `risk_score.py` | Weighted 0-100 composite score plus the per-component breakdown |
| `margin.py` | Initial and maintenance margin as functions of the score |
| `leverage.py` | Recommended max leverage, with the venue-wide cap |
| `open_interest.py` | Market-wide OI cap and per-account position limit, both anchored to depth |
| `liquidation.py` | Cushion above maintenance margin |
| `__init__.py` | `evaluate_risk()`, the single orchestrator |

One module per output family. To answer "where does the open interest cap come
from?", a reader opens one 50-line file.

### `risk_engine/v1/`

v1 is a separate package rather than a rewrite in place, so v0 keeps working and
the two can be compared on the same inputs. One module per *risk dimension*
instead of per output family, because in v1 the dimensions are the primitives
and the outputs are combinations of them.

| File | Responsibility |
| --- | --- |
| `units.py` | Time and scale conventions. 365 calendar days, one place |
| `provenance.py` | Whether a value was measured, fitted, assumed, or inherited from v0 |
| `inputs.py` | `MarketState`, `Interval`, and cross-field validation |
| `params.py` | `PolicyParameters`: what the venue chooses, kept separate from what the market imposes |
| `uncertainty.py` | D1, price uncertainty from staleness and source disagreement |
| `liquidity.py` | D2, liquidation cost and unwind horizon under power-law impact |
| `jumps.py` | D3, gap loss from a Pareto jump tail |
| `hedging.py` | D4, residual volatility and effective depth after hedging |
| `cascade.py` | D5, self-reinforcing liquidation and the open interest cap |
| `events.py` | Scheduled events acting on four channels, including the information channel |
| `regimes.py` | R1/R2/R3 preconditions and mechanism selection |
| `outputs.py` | `RiskOutputsV1`, with `tradable` nullable by construction |
| `__init__.py` | `evaluate_risk_v1()`, the single orchestrator |

The load-bearing structural choice is in `outputs.py`: `tradable` is `None`
whenever the market cannot support a continuous perp, so no consumer can render
a leverage number without first handling non-viability. `margin_diagnostics`
always carries the unconstrained requirement, unclamped, even above 100% of
notional.

### `backend/`

| Path | Responsibility |
| --- | --- |
| `app/main.py` | App factory, CORS, router wiring |
| `app/api/` | HTTP surface only: `health.py`, `risk.py` |
| `app/models/` | Request/response envelopes that reuse the engine's models directly, so the API cannot drift from the engine |
| `app/services/` | One-function adapter from request to engine call, per engine version |
| `app/config/` | Env-driven settings |
| `tests/` | Model validation, engine behaviour, API contract |

The backend is intentionally almost empty. If a code review finds arithmetic in
`backend/`, it is in the wrong place.

Two endpoints, one per engine:

| Endpoint | Engine | Notes |
| --- | --- | --- |
| `POST /risk/evaluate` | v0 | Frozen. Request and response shapes will not change |
| `POST /risk/v1/evaluate` | v1 | Takes `MarketState` plus optional `PolicyParameters`, echoes both back |
| `POST /risk/v1/frontier` | v1 | Sweeps a fixed staleness × volatility grid through the same evaluator, holding non-axis fields fixed; returns render-only cells |

The one piece of judgement in `services/risk_service.py` is that `evaluate_v1`
tags every field of an HTTP-supplied state as `ASSUMED`. Nothing arriving from a
slider is a measurement, and the provenance contract exists so the response
cannot imply otherwise. A caller with genuinely measured inputs calls
`evaluate_risk_v1` directly and supplies its own provenance map.

### `simulations/`

Standalone scripts, one per assumption under test, each reading a JSON scenario
from `simulations/scenarios/` so a run is reproducible from a file rather than
from edited constants. They import the engine the same way the API does.

### `frontend/`

Next.js App Router with TypeScript. `lib/types.ts` and `lib/typesV1.ts` mirror
the Pydantic models by hand; the models are small and stable enough that
generating them from the OpenAPI schema is not yet worth the build step.

The frontend has no risk logic. The viability-frontier map is produced by
``POST /risk/v1/frontier``, which sweeps the frozen axes through the same v1
evaluator while holding the console's non-axis inputs fixed. Live assessments
still come from ``POST /risk/v1/evaluate``. That keeps the browser from becoming
a second, silently diverging implementation of the model.

| Path | Responsibility |
| --- | --- |
| `app/page.tsx` | Tab between the v1 console and the v0 explorer |
| `components/V1Console.tsx` | v1 state, debounced evaluation |
| `components/V1InputForm.tsx` | Six primary drivers, the rest behind Advanced |
| `components/V1Outputs.tsx` | Viability, mechanism, regimes, limits, dimensions |
| `components/ViabilityFrontier.tsx` | Staleness × volatility mechanism map from `/risk/v1/frontier` |

## Deliberate omissions

No database, no auth, no caching, no containers, no CI. Evaluation is a pure
function of its inputs and runs in microseconds, so there is nothing yet to
persist or cache. These get added when there is a reason, not in advance.
