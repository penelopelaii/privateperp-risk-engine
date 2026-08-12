# Assumptions and limitations

An honest list of what v0 gets wrong.

**Most of this list is now the changelog for v1.** The linear blend, the single
scalar, the shaped margin curve, the scalar depth, and the unrepresented
liquidation horizon are all addressed in `risk_engine/v1/`; see
[`model_v1_spec.md`](model_v1_spec.md). This page is kept as written because v0
still ships, still backs `/risk/evaluate`, and the reasoning for replacing it is
worth reading before the replacement. Items v1 does **not** fix — correlation
between markets, funding rate — are called out below.

## Data

**Everything here is synthetic.** No proprietary, confidential, or internal data
of any kind is used, and none is welcome in this repository. The scenario files
and asset profiles are hand-written illustrations, so no result in this repo is
evidence about any real market. The engine's *structure* is the contribution;
its *numbers* are not.

## Structural assumptions

### The composite score is a linear blend

Risks are treated as substitutable: enough hedgeability can offset enough
illiquidity. This is the weakest assumption in the engine. Illiquidity and
unhedgeability almost certainly interact multiplicatively — an asset you can
neither price nor hedge is far worse than the sum of those two problems — and a
linear model will systematically under-price the corner of the input space this
project exists to study.

### Every output is a function of one scalar

Collapsing to a single score buys monotonicity and explainability, and costs the
ability to say "safe on average, with a specific tail". Two markets with
identical scores but different failure modes receive identical parameters today.

### The weights are judgement calls

The 0.25/0.20/0.20/0.15/0.10/0.10 split reflects a view about what matters, not
an estimate. Nothing in the repository yet justifies those numbers over any other
set summing to one.

### Margin is a shaped curve, not a loss quantile

Initial margin should answer "what loss do we need to cover over the expected
liquidation horizon, at what confidence?". Today it answers "what does a convex
curve from 2% to 60% give us?". The liquidation *horizon* is the genuinely
interesting variable here: seconds on a liquid perp, potentially weeks on an
illiquid one, and the current model never represents it explicitly.

### Depth is a single number

`market_depth` compresses an entire slippage curve into one scalar, which
implicitly assumes impact is linear in size. `data/synthetic/depth_curves.csv`
shows the curves the number is standing in for, and they are distinctly convex on
the illiquid profiles.

### No correlation between markets

Position limits are per-market. Several private-company exposures of the same
sector and vintage are close to a single position for liquidation purposes, and
the engine cannot currently see that. **Still true in v1.**

### No funding rate

A perp's funding rate is a primary risk lever, particularly when the underlying
cannot be arbitraged and the mark can drift indefinitely from any reference.
It is absent from v0 entirely. **Still true in v1**, and deliberately so: it is
listed as out of scope in the v1 specification.

## Known open results

- **Stale marks defeat the buffer.** `simulations/oracle_staleness.py` shows p95
  mark error still inside v0's liquidation buffer at a 7-day refresh (10.5%
  against 11.2%) and roughly double it by 30 days (23.2% against 12.2%). The
  crossover sits just past a week, and the buffer barely moves while the error
  quadruples. Either the buffer must scale far more aggressively with staleness, or
  infrequently-marked assets need a fundamentally different liquidation mechanism
  than continuous margin monitoring — the current answer of "widen the buffer a
  little" does not survive contact with the numbers. **v1 takes the second
  branch**, and `simulations/viability_frontier.py` shows where the mechanism
  stops working altogether.
- **Cascade dynamics are under-modelled.** The cascade simulation assumes a
  uniform account population and closes whole positions. Realistic leverage
  dispersion and partial liquidation would both change the result.
- **Jump parameters are invented.** Jump intensity and size in
  `simulations/scenarios/jump_risk.json` are guesses, so the loss quantiles are
  illustrations of a method rather than estimates of a risk.
