# Methodology

> Status: **v0 only.** Every number below is a placeholder heuristic chosen for
> explainability, not a calibrated estimate. The point of v0 was to fix the
> *shape* of the problem — which inputs matter, what they produce, and in which
> direction — so that a later version could replace the shapes with structure.
> That version exists: v1 is specified in [`model_v1_spec.md`](model_v1_spec.md)
> and shares none of the machinery below. This page documents what still backs
> `POST /risk/evaluate`.

## The chain

```
RiskInputs
   -> oracle reliability          (oracle.py)
   -> composite risk score 0-100  (risk_score.py)
   -> initial & maintenance margin (margin.py)
   -> max leverage                (leverage.py)
   -> OI cap & position limit     (open_interest.py)
   -> liquidation buffer          (liquidation.py)
```

Everything downstream of the score is a function of the score. That is a real
constraint, not an implementation detail: it guarantees monotonicity, so a
market that is worse on every input can never receive looser limits. The cost is
that the engine cannot yet express "this market is fine on average but has a
specific tail" — see [assumptions.md](assumptions.md).

## 1. Oracle reliability

Three inputs describe how well we know the price:

| Input | Meaning |
| --- | --- |
| `oracle_confidence` | Stated confidence in the feed |
| `price_staleness_days` | Age of the most recent observable mark |
| `oracle_dispersion` | Disagreement between sources, as a fraction of price |

They are collapsed into a single reliability in [0, 1]:

- Staleness decays exponentially with a **30-day half-life**. A same-day mark
  keeps its full value, a 30-day-old mark keeps half, a 90-day-old mark keeps an
  eighth.
- Dispersion decays linearly to zero at **25%** disagreement.
- The three are combined as a weighted average (0.45 / 0.35 / 0.20).

A weighted average is used because it is trivially auditable. It is also the
wrong functional form: it lets a strong confidence score paper over a mark that
is a year old. A multiplicative form is the likely successor.

## 2. Composite risk score

Six components, each normalised to [0, 1] where 1 is worst:

| Component | Weight | Source |
| --- | --- | --- |
| Illiquidity | 0.25 | `1 - liquidity_score` |
| Price discovery | 0.20 | Oracle penalty (above) |
| Jump risk | 0.20 | `jump_risk` |
| Unhedgeability | 0.15 | `1 - hedgeability_score` |
| Event proximity | 0.10 | `event_proximity` |
| Crowding | 0.10 | Open interest vs. 5x market depth |

The score is `100 x` the weighted sum, and the per-component contributions are
returned alongside it so any recommendation can be attributed.

Crowding is the only component that depends on the *current* state of the market
rather than the nature of the asset. It exists because identical assets are not
equally risky at different sizes: a position that fits inside available depth is
categorically different from one that must move the market to close.

## 3. Margin

Initial margin runs on a convex curve from **2%** at score 0 to **60%** at score
100, with curvature 1.5. Convexity keeps liquid markets competitively priced
while escalating quickly once a market is genuinely illiquid.

Maintenance margin is a fraction of initial margin that rises from **50%** to
**75%** as risk increases. The gap between initial and maintenance margin is the
room a trader has to be wrong before the venue intervenes, and it narrows on
risky assets — deliberately, because on an illiquid underlying the venue needs
to start unwinding earlier, not later.

## 4. Leverage

`1 / initial_margin`, clamped to [1x, 20x]. Leverage is reported separately from
margin because it is the number a trader actually sees and because the 20x cap
is a policy choice rather than a derived result.

## 5. Size limits

The open interest cap is a multiple of hedging depth, falling linearly from
**10x depth** at score 0 to **1x depth** at score 100. The per-account position
limit is a share of that cap, falling from **10%** to a floor of **2%**.

On an illiquid underlying these are the binding constraint. No margin level makes
a position safe if closing it would itself move the price several percent, which
is exactly what `simulations/liquidation_cascade.py` exists to test.

## 6. Liquidation buffer

A cushion above maintenance margin, expressed as a fraction of the maintenance
requirement: **10%** base, plus up to **40%** from the composite score and up to
**25%** from jump risk specifically. Jump risk gets its own term because the
composite score under-weights it: a gap can skip the liquidation price entirely,
so the buffer is the only thing standing between the venue and a bad debt.

## Validation

The parameterisation is not fit to data, so the simulations are the only check
that it is sane:

| Simulation | Question |
| --- | --- |
| `jump_risk.py` | Does recommended margin cover the loss distribution under discontinuous repricing? |
| `oracle_staleness.py` | Does the liquidation buffer cover the error in a stale mark? |
| `liquidation_cascade.py` | Does the OI cap keep forced unwinds from becoming self-reinforcing? |

The answer to the second is **no** once marks are older than about a week: p95
mark error is 10.5% against an 11.2% buffer at a 7-day refresh, and 23.2% against
12.2% at 30 days. The buffer barely moves while the error more than doubles. This
is the result that motivated v1, and `simulations/viability_frontier.py` is
v1's answer to it.
