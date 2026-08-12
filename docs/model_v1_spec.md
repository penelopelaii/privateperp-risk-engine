# Version 1 model specification

> **Status: revision 1.3 — implemented, tested, and reproducible.** The model
> described here is live in `risk_engine/v1/`, covered by 184 tests, and every
> number in this document is regenerated from the code rather than asserted. v0
> and the `/risk/evaluate` API are unchanged.
>
> Revision 1.2 locked five design decisions, added an output schema that can
> represent non-viability without clamping, and stated the headline finding.
> Revision 1.3 records what implementation changed:
>
> * **D1's structural term was rebuilt.** Revision 1.2's `eta` penalty violated
>   the document's own monotonicity guarantee; it is replaced by withdrawing the
>   averaging credit, and `eta` is deleted. **This dimension is now locked.**
> * **D5 was re-derived from first principles.** The cascade is closed on a single
>   observable, and `Q_max`'s elasticity to `phi_1` is exactly `-1`, not `-1/alpha`.
> * **R2 is reclassified** as an operational observability constraint rather than
>   a risk condition. Behaviour unchanged.
> * **The headline finding is now reproducible** from a recorded profile via
>   `python -m simulations.viability_frontier`.
>
> Revision 1.1's review findings are retained, condensed, in
> [Appendix A](#appendix-a-review-findings-carried-forward-from-revision-11).

---

## Locked decisions

These are settled. Implementation follows them; reopening any of them is a change
request against this document.

**L1. The liquidation mark is a robust external reference.** The perp's own order
book is **never** substituted as the mark, at any level of staleness. When the
external reference is too stale or too uncertain, the model triggers a regime
switch (see [regime switches](#regime-switches)) rather than falling back to an
internal price. Rationale: the underlying is by construction unhedgeable and
un-arbitrageable, so nothing anchors the perp book to fundamental value; marking
to it would convert price risk into manipulation risk and report the result as a
*lower* risk number. Manipulation-resistant blended marks are
[explicitly out of scope](#out-of-scope-for-v1).

**L2. `sigma` is a first-class required input.** It is the model's single largest
driver and v1 will not infer it silently. The v0 compatibility adapter may supply
a synthetic value, but it must be tagged
`provenance = INFERRED_FROM_V0` and must never be presented as calibrated.

**L3. Required margin is never clamped at 100%.** When required initial margin
reaches or exceeds notional, the model returns the unconstrained figure as a
diagnostic, sets `viable_as_continuous_perp = false`, and names an alternative
mechanism. Sub-1x leverage is never emitted as a normal perp recommendation.

**L4. All time is calendar, `A = 365`.** v1, the v0 adapter, and every simulation
use the same convention. All volatility and jump-intensity inputs must be
calendar-annualised, and this is enforced at input validation. `simulations/`
was moved from 252 to 365 as a prerequisite of this revision, and
`test_units.py` asserts that the simulations and the engine agree.

**L5. `phi_1` is observable venue state in principle, unobservable here.** It has
no default. Callers supply either a point value or an interval; when an interval
is supplied — which is the expected case for this research prototype — the open
interest cap is reported as a **range**, never as a point estimate.

---

## Headline finding

**Continuous mark-based margining is not a parameter setting that can always be
tightened. It is a mechanism with preconditions, and on a sufficiently illiquid,
sufficiently stale underlying those preconditions fail outright.**

Under dimensionally correct units, an asset with 90% annualised volatility and an
illiquid profile degrades like this as its mark ages. Every figure below is
produced by `python -m simulations.viability_frontier`, from the profile recorded
in that file:

| Mark staleness | sigma_U | Maintenance | Initial | Max leverage | Status |
| --- | --- | --- | --- | --- | --- |
| 0d | 5.2% | 46.5% | 70.8% | 1.41x | viable |
| 1d | 7.0% | 50.1% | 74.5% | 1.34x | viable |
| 7d | 13.5% | 63.1% | 110.5% | - | **not viable (R1, R2)** |
| 14d | 18.4% | 72.8% | 136.7% | - | **not viable (R1, R2)** |
| 30d | 26.3% | 88.7% | 178.0% | - | **not viable (R1, R2)** |
| 120d | 51.9% | 139.8% | 303.0% | - | **not viable (R1, R2, R3)** |

The naive reading is "risky assets need more margin, and at 120 days they need
303%, which is merely impractical." That reading is wrong, because three distinct
preconditions fail, and only the first is about the *amount* of collateral.

**1. Solvency: above 100% margin the instrument is no longer a perp.** A contract
requiring more collateral than notional is a prepaid forward with extra steps —
and a worse one, since it retains funding payments and liquidation risk while
offering no leverage. It is not a conservative perp; it is a different, dominated
product. Anyone still willing to trade it wants unlevered exposure and is better
served by a settled instrument.

**2. Information: the trigger stops being informative.** At 120 days the mark is
uncertain to about 52%, and the buffer needed to keep wrongful liquidations
within tolerance reaches 163% of notional — marginally more than the entire
cushion between initial and maintenance margin. Liquidation
decisions become close to uncorrelated with actual solvency: the venue liquidates
accounts that are fine and misses accounts that are not. **Higher margin does not
fix this**, because margin governs the loss you can absorb, not the accuracy of
the measurement that triggers absorption. You cannot repair a broken speedometer
by lowering the speed limit.

**3. Timing: there is no state feedback during the unwind.** When the mark
refreshes less often than a liquidation takes to execute, the venue cannot
observe the state it is supposedly managing continuously. "Continuous margining"
presumes a continuously observable state; here the state is observed a few times
a year. This condition (R2) is **independent of volatility and of margin level** —
no collateral schedule makes an unobservable state observable.

The failure is therefore in the **trigger and the exit**, not in the **amount**,
and the correct response is a change of mechanism: a periodic auction that only
makes decisions at moments when a price genuinely exists, or a fully-collateralised
settled forward with no path-dependent liquidation at all.

The transition is also sharper than the inputs suggest. Parameters drift smoothly
while the mechanism holds, and then stop existing:

| sigma | R3 first trips | R1 first trips | R2 first trips |
| --- | --- | --- | --- |
| 30% | 0d | 27d | 5d |
| 50% | 0d | 14d | 5d |
| 80% | 17d | 7d | 5d |
| 100% | 87d | 4d | 5d |
| 120% | 126d | 3d | 5d |

R3 trips at zero staleness for the lower-volatility rows because the assumed 5%
source dispersion already exceeds the one-day diffusion cushion — which is the
"dispersion must be read relative to volatility" point made concrete: 5%
disagreement is noise on a 120% asset and a structural pricing failure on a 30%
one.

The R2 column is flat at 5 days for every asset because
[R2 is an operational constraint, not a risk measurement](#r2-is-an-operational-observability-constraint-not-a-risk-measurement):
it compares the venue's data cadence against its own tolerated unwind horizon and
never consults the asset.

**Read the R3 column with caution.** Away from zero staleness the two sides of R3
are nearly equal — the required buffer stays within one percentage point of the
available cushion from 7 days to 120 — because `z_eps = z_theta` makes the
comparison approximately `sigma_U` against `sigma_resid * sqrt((tau_r + tau_d)/A)`
on a barely-hedgeable asset where those are almost the same number. The *day* R3
first trips is therefore sensitive to small parameter changes, even though whether
it eventually trips is not. R1 and R2 carry the finding; R3 corroborates it.

**Why this matters beyond the model.** The research question asks how risk
parameters should change as an asset becomes less liquid and harder to price. The
answer this model gives is that for part of that spectrum there is no admissible
set of parameters, and the honest output is a different instrument. A risk engine
that can only return numbers will always return one, which is precisely how a
venue ends up listing something it should not have.

---

## Time and unit conventions

```
A     = 365      calendar days per year          (L4)
T_ref = 1 day    reference period for impact
```

Horizons are stored in **days** and converted at the point of use;
`tau_years = tau_days / A`. Calendar rather than trading days because
information decay on an asset that reprices a few times a year is a calendar
process, and because a single convention removes a whole class of bug.

`sigma`, `sigma_h`, and `lambda` must be calendar-annualised. Input validation
rejects values flagged as trading-annualised rather than silently rescaling.

Every equation below annotates the units of both sides. `[ - ]` denotes a
dimensionless quantity (returns and probabilities are dimensionless).

---

## Inputs

### Measurement

| Symbol | Name | Units | Required |
| --- | --- | --- | --- |
| `sigma` | Return volatility, calendar-annualised | year^-1/2 | **yes (L2)** |
| `D_spot` | Spot depth | USD/day | yes |
| `D_hedge` | Hedge venue depth, hedge-instrument notional | USD/day | no (default 0) |
| `sigma_h` | Hedge instrument volatility | year^-1/2 | if `D_hedge > 0` |
| `rho_h` | Correlation of hedge to underlying | [-1, 1] | if `D_hedge > 0` |
| `H` | Fraction of notional hedged | [0, 1] | yes |
| `alpha`, `gamma` | Impact exponent and coefficient at `T_ref` | -, fraction | yes |
| `tau_stale` | Age of the current mark | days | yes |
| `tau_d` | Expected mark refresh interval | days | yes |
| `delta` | Source dispersion | fraction of price | if `n_src > 1` |
| `n_src`, `rho_src` | Source count, inter-source correlation | count, [0,1] | yes |
| `lambda`, `xi`, `m0` | Jump intensity, log-tail index, tail scale | year^-1, -, log-return | yes |
| `OI_long`, `OI_short` | Directional open interest | USD | yes |
| `phi_1` | Share of OI within a 1% move of its trigger | point or interval | **yes, no default (L5)** |
| event block | See [event taxonomy](#event-taxonomy) | | no |

`delta` is **undefined when `n_src = 1`** and must be absent rather than zero; one
source cannot disagree with itself. Validation rejects `delta` supplied alongside
`n_src = 1`.

### Policy

`tau_r` response horizon (days), `tau_u_max` maximum tolerable unwind (days),
`rho_part` participation rate, quantiles `z_theta`, `z_phi`, `z_psi`, `z_eps`,
tolerances `eps_jump`, `eps_spurious`, cascade ceiling `beta_max`, insurance fund
size, `L_policy`.

### Provenance

Every parameter carries a provenance tag, and it propagates to the outputs (L2):

```
MEASURED           observed from the venue or market
FITTED_SYNTHETIC   fitted to data this repository fabricated
ASSUMED            a declared judgement
INFERRED_FROM_V0   produced by the v0 compatibility adapter
```

Any output whose computation consumed an `ASSUMED`, `FITTED_SYNTHETIC`, or
`INFERRED_FROM_V0` input carries `contains_assumed_inputs = true`. In this
repository that is every output; the flag exists so that it stops being true one
parameter at a time as real data arrives.

---

## D1. Price uncertainty

The mark is a **robust external reference** (L1): a trimmed median over `n_src`
independent external sources, never the perp book.

```
sigma_U^2 = sigma^2 * (tau_stale / A)                       [ - ]
          + kappa_rob * delta^2 * w_eff                     [ - ]

w      = rho_src + (1 - rho_src) / n_src        averaging credit
       = 1                                      if n_src = 1

w_eff  = w + (1 - w) * min(1, max(0, r_dd - 1)) in [w, 1]

r_dd   = delta / (sigma * sqrt(tau_min / A))                [ - ]

delta  = delta_prior  if n_src = 1
tau_min = 1 day       minimum information horizon
```

`kappa_rob ~= pi/2` is the asymptotic efficiency cost of a median relative to a
mean under normality. **Robustness is not free**: choosing a manipulation-resistant
estimator inflates sampling variance by about 57%, and L1 accepts that cost
deliberately in exchange for not being movable by one corrupted source.

The averaging credit `w` floors variance at `rho_src * delta^2`, so ten feeds
copying one primary are worth little more than one.

**The structural-disagreement term.** `r_dd` asks whether sources disagree by more
than the asset's volatility can explain. Above 1, the disagreement is evidence of
*common* error rather than independent noise — and averaging does not remove
common error. The response is therefore to **withdraw the averaging credit**,
interpolating `w_eff` from `w` up to 1, at which point `n_src` sources are treated
as one. That ceiling is the strongest claim the disagreement data alone supports,
and it is what removes the need for a tuned coefficient: revision 1.2's free
parameter `eta` is **deleted**.

The ceiling is not airtight. If every source errs in the same direction, true
uncertainty can exceed even the un-averaged spread, and this term cannot express
that. A consequence worth stating: once disagreement is structural, `n_src` and
`rho_src` stop affecting the result entirely.

**`tau_min` and the window.** `r_dd` is evaluated at a **fixed** one-day window,
not at the elapsed staleness. Whether disagreement is structural is a property of
how the asset is priced, not of how old today's mark happens to be — which is the
"dispersion must be read relative to volatility" point: 5% disagreement is noise
on a 120% asset and a pricing failure on a 30% one. Revision 1.2 let the window
grow with `tau_stale`, which made the whole term decay as the mark aged; on a
high-dispersion asset it decayed faster than the drift term accumulated, so
`sigma_U` fell from 35.6% at one day to 28.4% at seven before recovering. A staler
mark reported as more reliable is the v0 defect this dimension exists to remove.

Fixing the window also makes `r_dd` well defined at `tau_stale = 0`, where
diffusion over the elapsed window is zero.

The drift term `sigma^2 * (tau_stale / A)` is never floored and remains exactly
zero at `tau_stale = 0`, so at zero staleness `sigma_U` is pure source dispersion.
This preserves the economic interpretation of the 0-day rows in the
[viability frontier](#headline-finding): R3 still trips for low-volatility assets
because 5% disagreement exceeds their one-day diffusion cushion.

Since nothing but the drift term depends on `tau_stale`, `sigma_U` is now monotone
increasing in staleness by construction.

- *Principled:* variance accumulation in time; the averaging credit; the median
  efficiency factor; the diagnostic ratio; the `1/w` ceiling.
- *Placeholder:* `delta_prior`; `tau_min`; the exact `kappa_rob` for a trimmed
  rather than pure median.

## D2. Liquidity and liquidation cost

```
v(q)     = q / (D_eff * T_ref)                              [ - ]  "days of depth"
tau_u(q) = q / (rho_part * D_eff)                           [ days ]
C(q)     = gamma * v(q)^alpha                               [ - ]
         + z_phi * sigma * sqrt(tau_u(q) / (3 * A))         [ - ]
```

The `1/3` is the average-inventory correction for a linear liquidation
trajectory. `T_ref` makes the impact argument dimensionless and must accompany
every use of the fitted `alpha`, `gamma`.

The liquidity x hedgeability interaction is **not imposed here**. Hedgeability
enters only through `D_eff`; because `C` is convex in `v` (fitted `alpha` reaches
1.14 on illiquid profiles), degrading depth and hedge quality together compounds
automatically.

## D3. Jump risk

Jump sizes are **log-returns**, so losses respect limited liability:

```
Pbar(y)  = (y / m0)^(-xi)          for y >= m0             [ - ]
m_J(tau) = m0 * max(1, lambda * (tau/A) / eps_jump)^(1/xi)  [ log-return ]
loss_J   = 1 - exp(-m_J)                                    [ - ]
```

The `max(1, .)` clamp keeps evaluation inside the Pareto's domain of validity and
restores monotonicity in tail heaviness. When `lambda * tau / A < eps_jump` the
constraint does not bind: no jump exceeding `m0` is expected within tolerance over
that horizon.

`xi <= 1` implies infinite mean, so only quantile-based outputs are permitted
unless `xi > 1` is asserted. Validation warns when `xi <= 1`.

## D4. Hedgeability

Bounded by construction via the minimum-variance hedge, with
`beta_mv = rho_h * sigma / sigma_h`:

```
sigma_resid^2 = sigma^2 * [1 - rho_h^2 * (2H - H^2)]        [ year^-1 ]
              in [ sigma^2 * (1 - rho_h^2),  sigma^2 ]      always

D_eff = D_spot + H * |rho_h| * (sigma_h / sigma) * D_hedge  [ USD/day ]
```

Capacity and variance reduction are different quantities and do not share a
coefficient: offsetting one unit of exposure requires `beta_mv` units of the hedge
instrument, while the risk removed scales with `rho_h^2`; combining them yields
the linear `|rho_h|` term above. `D_eff` is monotone increasing in `|rho_h|` and
never falls below `D_spot`.

**Edge case: `rho_h = 0`.** The intermediate form `rho_h^2 * (D_hedge / beta_mv)`
is `0/0` at zero correlation, since `beta_mv = rho_h * sigma / sigma_h` vanishes
with `rho_h`. The implementation therefore evaluates the **simplified expression
directly**, never the quotient:

```
D_eff = D_spot + H * |rho_h| * (sigma_h / sigma) * D_hedge
```

This is continuous at `rho_h = 0`, where it correctly returns `D_eff = D_spot`: a
hedge instrument uncorrelated with the underlying contributes no exit capacity.
The two forms are algebraically identical wherever `rho_h != 0`.

`sigma > 0` is required (it appears in the denominator) and is enforced at input
validation; a zero-volatility asset is outside the model's domain.

## D5. Concentration and cascade

Uses **directional** open interest on the shocked side (`Q = OI_long` for a
downward shock). With `g(l) = gamma * (l / (D_eff * T_ref))^alpha`:

```
fixed point: x       = x_0 + g(Q * F_B(x))
             beta(x) = alpha * gamma * v^alpha * F_B(x)^(alpha-1) * f_B(x)   [ - ]
             Phi     = 1 / (1 - beta)          for beta < 1

             v       = Q / (D_eff * T_ref)                                   [ - ]
```

### Closing `F_B` on one observable

Only `phi_1 = F_B(x_ref)` at `x_ref = 1%` is observable, so the distribution is
closed with the minimal assumption available: **`F_B` is linear on the reference
interval**, capped at 1. That single closure supplies both quantities the
derivative needs, consistently:

```
F_B(x) = min(1, phi_1 * x / x_ref)          f_B = phi_1 / x_ref
```

Revision 1.2 instead took `F_B = 1` and `f_B = phi_1 / x_ref` together, which are
not two facts about the same distribution. Substituting the closure at `x = x_ref`
collapses the derivative to

```
beta  = (alpha * gamma / x_ref) * (v * phi_1)^alpha                       [ - ]

Q_max = D_eff * T_ref * ( beta_max * x_ref / (alpha * gamma) )^(1/alpha)
        / phi_1                                                         [ USD ]
```

`Q` and `phi_1` enter only through the product `v * phi_1` — the notional a 1%
move puts up for sale, measured in days of depth, which is the quantity cascade
risk actually depends on. Two exact consequences follow, both now asserted in
`test_cascade.py`:

* `Q_max` is **exactly linear** in `D_eff`.
* `Q_max` is **exactly inversely proportional** to `phi_1`, for every `alpha`.
  The elasticity is `-1`, not revision 1.2's `-1/alpha`, which was an artifact of
  the inconsistent pairing.

### The evaluation point is a choice

`beta` varies with the shock, so naming the shock is unavoidable. Under the
closure, `beta(x) ∝ x^(alpha-1)` up to the point where everyone is liquidated:

* **`alpha > 1`:** `beta` rises with the shock. A cap sized at `x_ref` is
  therefore **not conservative against larger shocks**. The worst case is
  bounded — at `x = x_ref / phi_1` every account is out and `f_B` falls to zero —
  and equals `phi_1^(1-alpha)` times the reference value: 1.57x for
  `alpha = 1.15, phi_1 = 5%`, which turns `Phi = 2.0` into `Phi = 4.5`.
* **`alpha < 1`:** `beta` diverges as the shock vanishes. This is an artifact of
  concave impact having unbounded marginal impact at zero size, not a finding: a
  vanishing shock also liquidates a vanishing notional. It does mean **no
  shock-independent supremum exists**, so a declared reference shock is the only
  well-posed option. The fitted `alpha` spans 0.74 to 1.18, so this case is
  reachable and the model must handle it.

A uniformly conservative variant is available and **not** adopted: evaluate at
`max(phi_1^(alpha-1), 1)`, taking the worse of the two candidate points. It would
raise the cap for `alpha < 1` and lower it for `alpha > 1`. Recorded as an option
rather than applied, because it answers a different question — "stable against
any shock" instead of "stable against a 1% shock" — and the reference-shock
reading is the one `phi_1` is defined against.

### Remaining `F_B` caveats

1. **No atoms** is assumed by the derivative test, and is empirically false —
   clustering at maximum leverage puts an atom at buffer `IM - MM`. A **discrete
   condition** is therefore also required: the fixed-point iteration must
   terminate, verified by simulation, not by derivative.
2. **`F_B` is a state variable, not a parameter.** Buffers depend on entry
   leverage *and* the path since entry, so it cannot be recovered from the
   leverage distribution alone.

Sensitivity for `synth_private_a` (`alpha = 1.149`, `gamma = 0.0703`,
`D_eff = $350,196/day`), reproducible from `data/synthetic/asset_profiles.json`
through the v0 adapter:

| `phi_1` | 1% | 2% | 5% | 10% | 20% | 40% |
| --- | --- | --- | --- | --- | --- | --- |
| `Q_max` | $3.11m | $1.55m | $0.62m | $0.31m | $0.16m | $0.08m |

The 10x range across L5's `[2%, 20%]` interval gives exactly a 10x range in the
cap. Hence L5: an interval in, a range out. Reporting a point estimate here would
be the single most misleading number the engine could produce.

---

## Output mapping

```
q_max  = rho_part * D_eff * tau_u_max                                  [ USD ]

MM(q)  = C(q) + z_phi * sigma_U + (1 - exp(-m_J(tau_u(q))))            [ - ]

IM(q)  = MM(q)
       + z_theta * sigma_resid * sqrt((tau_r + tau_d) / A)             [ - ]
       + (1 - exp(-m_J(tau_r + tau_d)))                                [ - ]

L_max  = min( 1/IM,  1/(1 - exp(-m_J(tau_r))),  L_policy )             [ x ]

b      = z_psi * sigma_U + (1 - exp(-m_J(tau_d)))                      [ - ]
```

`IM` and `MM` are **unbounded above** (L3). `b` is a fraction of notional, not of
maintenance margin.

---

## Regime switches

Three independent conditions, each interpretable on its own, none circular in the
quantity it constrains. **R1 and R3 are risk conditions; R2 is not** — see below.

```
R1  viability        IM(q) >= 1                                    [ risk ]
    Required margin meets or exceeds notional: the product is not leveraged.

R2  observability    tau_d >= tau_u(q_max)  <=>  tau_d >= tau_u_max  [ operational ]
    The mark does not refresh even once during a full unwind, so there is no
    state feedback during the only period in which the venue is acting.

R3  signal-to-noise  z_eps * sigma_U + (1 - exp(-m_J(tau_d))) > IM - MM   [ risk ]
    The buffer needed to hold wrongful liquidations below eps_spurious does not
    fit inside the cushion between initial and maintenance margin.
```

### R2 is an operational observability constraint, not a risk measurement

Evaluated at the position limit, R2 is an identity away from being a comparison
of two policy inputs. `q_max` is *defined* as the position that unwinds in
`tau_u_max`, so `tau_u(q_max) = tau_u_max` exactly, and R2 reduces to

```
tau_d >= tau_u_max
```

No market data enters: not depth, not volatility, not impact. This is not a
defect to be repaired, and revision 1.2's claim that R2 is "independent of `sigma`
and of margin level" was understating it — R2 is independent of the *asset*.

What R2 actually asserts is a precondition on the venue's own operating model:
**you cannot run a continuously-margined book on a data feed slower than your own
tolerated unwind horizon.** Both sides are things the venue chooses — how often it
can obtain a mark, and how long it is willing to be mid-liquidation — and the
condition says those two choices must be compatible. It belongs with the mechanism
question, not with the five risk dimensions, and it is the one condition whose
answer a venue can change by procurement rather than by pricing.

Consequences of that reading, all intended:

* R2 fires at the same staleness for every asset (5 days under the default
  `tau_u_max`), which is why it appears as a flat column in the frontier.
* It cannot be relieved by more collateral, lower leverage, or a smaller cap.
* It *can* be relieved by shortening `tau_u_max` — accepting a faster, more
  costly liquidation — which correctly shows up as higher `C(q)` and therefore
  higher maintenance margin. The trade-off is represented, just not inside R2.

**Alternative considered and rejected.** A genuinely market-derived observability
condition would compare the refresh interval against the time for the price to
plausibly consume the maintenance margin, `tau_d >= A * (MM / sigma)^2`. It is
economically meaningful, but it measures the same thing R3 already measures —
whether the trigger is informative — while losing the operational statement that
R2 uniquely makes. Behaviour is therefore unchanged.

### Mechanism selection

| Triggered | `viable_as_continuous_perp` | `recommended_mechanism` |
| --- | --- | --- |
| none | true | `CONTINUOUS_PERP` |
| R2 or R3 only | false | `PERIODIC_AUCTION`, cadence `>= tau_d` |
| R1 (any combination) | false | `SETTLED_FORWARD`, fully collateralised |
| R1 and no mark within contract term | false | `NOT_LISTABLE` |

R2 or R3 alone means the *decisions* are unsound while the *collateral* is
adequate, so the fix is to make decisions only when a price exists. R1 means the
collateral requirement has eliminated leverage, so the fix is to stop pretending
the instrument is leveraged.

---

## Output schema proposal

Designed so non-viability is representable without clamping, and so a sub-1x
leverage figure **cannot** be rendered as a normal recommendation (L3). This is a
new `RiskOutputsV1`; the v0 `RiskOutputs` is untouched.

```python
class Mechanism(str, Enum):
    CONTINUOUS_PERP = "continuous_perp"
    PERIODIC_AUCTION = "periodic_auction"
    SETTLED_FORWARD  = "settled_forward"
    NOT_LISTABLE     = "not_listable"


class RegimeTrigger(BaseModel):
    """One failed precondition, with the numbers that failed it."""
    id: Literal["R1", "R2", "R3"]
    description: str
    measured: float
    threshold: float


class RiskDimensions(BaseModel):
    """Always populated. Diagnostic, and independent of viability."""
    price_uncertainty: float          # sigma_U
    effective_depth: float            # USD/day
    liquidation_cost_at_limit: float  # C(q_max)
    unwind_days_at_limit: float       # tau_u(q_max)
    jump_quantile_response: float     # loss_J over tau_r + tau_d
    jump_quantile_unwind: float       # loss_J over tau_u
    cascade_beta_at_cap: float


class MarginDiagnostics(BaseModel):
    """Unconstrained requirements. NOT clamped to 1.0 (L3)."""
    required_initial_margin: float = Field(ge=0)       # no upper bound
    required_maintenance_margin: float = Field(ge=0)   # no upper bound
    implied_leverage: float = Field(gt=0)              # may be < 1; diagnostic only


class SizeLimits(BaseModel):
    """Valid regardless of margining mechanism; an auction needs limits too."""
    position_limit: float
    open_interest_cap_low: float
    open_interest_cap_high: float
    open_interest_cap_point: float | None   # only when phi_1 is a point value
    phi_1_low: float
    phi_1_high: float


class TradableParameters(BaseModel):
    """Populated ONLY when viable_as_continuous_perp is true."""
    max_leverage: float = Field(ge=1.0)     # >= 1 by construction here
    initial_margin: float = Field(gt=0, le=1.0)
    maintenance_margin: float = Field(gt=0, le=1.0)
    liquidation_buffer: float = Field(ge=0)


class RiskOutputsV1(BaseModel):
    viable_as_continuous_perp: bool
    recommended_mechanism: Mechanism
    triggered_regimes: list[RegimeTrigger]

    tradable: TradableParameters | None     # None whenever not viable
    margin_diagnostics: MarginDiagnostics   # always present, unclamped
    size_limits: SizeLimits
    dimensions: RiskDimensions

    contains_assumed_inputs: bool
    provenance: dict[str, Provenance]
    engine_version: str
```

Four properties this buys, each mapping to a locked decision:

- **The numeric result is never hidden.** `margin_diagnostics.required_initial_margin`
  is 2.675 for the 120-day case and is reported as such (L3).
- **A non-viable market cannot be rendered as a tradable one.** `tradable` is
  `None`, so a consumer that wants a leverage figure must first handle the
  viability case. A clamped 0.37x could have been rendered in a card; `None`
  cannot.
- **Size limits survive non-viability**, because an auction or forward still needs
  them, and they do not depend on the margining mechanism.
- **Assumption status travels with the answer** (L2), rather than living only in
  documentation.

Consumers must branch on `viable_as_continuous_perp`. That is deliberate friction.

---

## Event taxonomy

Events act on four channels with type-dependent signs. Not every event improves
liquidity.

| Event type | Jump | Info | Liquidity | Comparability |
| --- | --- | --- | --- | --- |
| Priced round, disclosed | up | improves | none | intact |
| Priced round, undisclosed | up | **none** | none | intact |
| Down round / recap | large | improves | none | **breaks** |
| Secondary tender | moderate | improves, then decays | up, **temporary** | intact |
| IPO / direct listing | large | improves | up, **delayed by lockup** | intact |
| Lockup expiry | small | none | up | intact |
| M&A, cash | large on break | collapses to spread | converges to cash | terminal |
| M&A, stock | large on break | partial | tracks acquirer | changes underlying |
| Regulatory / litigation | large | improves | none | intact |
| Public earnings | moderate | improves | none | intact |

Four consequences the implementation must represent:

1. **An undisclosed round is pure downside** — jump risk rises with no offsetting
   information gain. The information channel is gated on disclosure, not on the
   event occurring.
2. **IPO liquidity is delayed and separate from hedgeability.** During a 90-180
   day lockup, listed options and borrow can appear (`H` up) while holders still
   cannot sell (`D_spot` flat). The two move on different schedules.
3. **A recap can raise `sigma_U` after the event**, because a new preference stack
   makes prior marks non-comparable. The information channel can be negative.
4. **Lockup expiry is a drift, not a symmetric jump.**

Modelling form: a scheduled, deterministic-date jump (not an intensity bump)
active when `tau_r > tau_E`; plus `tau_d_fwd = min(tau_d, tau_E + eps)` gated on
disclosure; plus a type-specific, possibly delayed liquidity schedule.

The **crossover** is an acceptance test: approaching a disclosed event, margin and
leverage tighten while the buffer loosens. Opposite signs on different outputs is
correct.

---

## Estimated versus assumed

**Empirically estimated: 2 of 31 parameters — and the estimation is not
empirical.**

| Parameter | Provenance | Basis |
| --- | --- | --- |
| `alpha`, `gamma` per profile | `FITTED_SYNTHETIC` | `data/synthetic/depth_curves.csv`, R^2 > 0.99 |
| `alpha(L)`, `gamma(L)` projection | `FITTED_SYNTHETIC` | 2 coefficients from 5 hand-written points |

Those R^2 values measure **internal consistency of data this repository
invented**, not agreement with any market, and five hand-authored points support
no inference: no standard errors, no held-out validation, not independent draws.
This is why `FITTED_SYNTHETIC` is a distinct provenance value from `MEASURED`.

Everything else is `ASSUMED`: `sigma` when adapted from v0, `rho_h`, `sigma_h`,
`D_hedge`, `n_src`, `rho_src`, `delta_prior`, `tau_min`, `kappa_rob`, `lambda`, `xi`,
`m0`, `phi_1`, `beta_max`, `tau_r`, `tau_d`, `tau_u_max`, `rho_part`, `T_ref`,
`z_theta`, `z_phi`, `z_psi`, `z_eps`, `eps_jump`, `eps_spurious`, insurance fund
size, `L_policy`, and every entry in the event table.

Ranked by influence: `sigma` (drives everything), `phi_1` (10x range in `Q_max`
across L5's interval, since the elasticity is exactly `-1`), `lambda`/`xi`
(leverage cap), `tau_d` (all three regime switches), `rho_part` (unwind horizon,
hence position limit).

---

## Consistency guarantees

| Property | Status | Basis |
| --- | --- | --- |
| `IM > MM` | holds | `IM = MM +` two strictly positive terms, plus an epsilon floor |
| `sigma_U` increasing in `tau_stale` | holds | Only the drift term depends on `tau_stale`; the diagnostic window is fixed |
| `IM` may exceed 1 | **by design (L3)** | Reported unclamped; R1 handles the consequence |
| `tradable` implies `leverage >= 1` | holds | `tradable` is `None` whenever R1 fires |
| Leverage decreasing in jump risk | holds | Both channels decrease in `lambda` and tail heaviness, given the `m_J >= m0` clamp |
| `q_max` increasing in `D_eff` | holds | Linear by construction |
| `Q_max` increasing in `D_eff` | holds | Exactly linear; `beta` depends on `Q` only via `Q/D_eff` |
| `MM` increasing in `q` | holds | `C` increasing and convex in `q` |
| Regime switches defensible | holds | R1/R2/R3 independent and individually interpretable |
| Monotone in event proximity | **not enforced** | Four channels, type-dependent signs |
| Monotone in gross OI | **not enforced** | Directional OI drives cascade; gross OI is partly a liquidity signal |
| Monotone in dispersion at the low end | **not enforced** | `delta -> 0` informative only when `n_src > 1` |

---

## v0 compatibility adapter

Preserves `/risk/evaluate` and the frontend unchanged. Every value below is
tagged `INFERRED_FROM_V0` and surfaces as `contains_assumed_inputs = true` (L2).

```
alpha  = 1.184 - 0.440 * liquidity_score          # FITTED_SYNTHETIC, R^2 = 0.84
gamma  = exp(-2.450 - 2.560 * liquidity_score)    # FITTED_SYNTHETIC, at T_ref = 1 day
sigma  = 0.30 + 0.45*(1 - liquidity_score) + 0.30*jump_risk    # INFERRED_FROM_V0
rho_h  = sqrt(hedgeability_score)                 # INFERRED_FROM_V0
D_spot = market_depth                             # REINTERPRETED as USD/day
OI_long = current_open_interest                   # v0 cannot see direction
phi_1  = interval [0.02, 0.20]                    # INFERRED_FROM_V0, forces a range
```

Two semantic changes the adapter must document loudly: `market_depth` is
reinterpreted from a stock to a rate, and `phi_1` is supplied as an interval so
that a v0-sourced call can never produce a point open interest cap.

---

## Validation targets

| Test | Target |
| --- | --- |
| `jump_risk.py` | `P(loss > IM) ~= eps_jump` |
| `oracle_staleness.py` | p95 mark error `<= b`, or R2/R3 trips |
| `liquidation_cascade.py` | realised amplification `<= 1/(1 - beta_max)` at `Q = Q_max`, **including an atom at maximum leverage** |
| dimensional invariance | every output unchanged when horizons are supplied in days vs years |
| time convention | v1 and all simulations agree on `A = 365` (L4) |
| `phi_1` sweep | `Q_max` reported as a range; cascade stable across the whole interval; elasticity exactly `-1` |
| cascade derivation | collapsed `beta` equals the general derivative at the reference shock, across `alpha` and `phi_1` |
| viability frontier | the headline table is *generated* by `simulations/viability_frontier.py`, not compared against |
| schema | `tradable is None` whenever `viable_as_continuous_perp` is false, and `required_initial_margin` is never clamped |

---

## Implementation, as built

```
risk_engine/
  v1/
    params.py        # policy parameters and declared assumptions, one place
    units.py         # A = 365, T_ref; the ONLY place conversions appear
    provenance.py    # Provenance enum and propagation
    inputs.py        # MarketState, Interval
    uncertainty.py   # D1, robust external reference mark
    liquidity.py     # D2, T_ref-aware impact curve
    jumps.py         # D3, log-space, domain-clamped
    hedging.py       # D4, bounded
    cascade.py       # D5, linear buffer closure + phi_1 range
    regimes.py       # R1/R2/R3, Mechanism, and selection
    events.py        # event taxonomy and channel signs
    outputs.py       # RiskOutputsV1 assembly
    __init__.py      # evaluate_risk_v1()
  v0_adapter.py      # projection, tagged INFERRED_FROM_V0
simulations/
  viability_frontier.py   # regenerates the headline finding
```

`calibration/impact.py` was not created; the fitted constants are inlined in
`v0_adapter.py` with their provenance, since nothing else consumes them yet.

**Prerequisite changes to existing code, completed:**

1. `simulations/*` moved from 252 to 365 (L4). Published simulation numbers
   changed, and `README.md`'s staleness result was regenerated: the p95 mark
   error now crosses the v0 buffer at about ten days rather than seven.
2. `data/README.md` states that `market_depth` is a **rate** (USD/day) under v1's
   reading. The file is at `data/README.md`, not `data/synthetic/README.md`.
3. `backend/tests/test_risk_engine.py`'s blanket monotonicity test was split into
   six per-relationship assertions from
   [consistency guarantees](#consistency-guarantees), plus one characterisation
   test pinning v0's saturation above 5x depth.

No changes to `risk_engine/`'s v0 modules, the v0 API, or the frontend.

---

## Implementation notes (engine 1.0.0)

A change log of what implementation forced back into the specification. **No open
discrepancies remain**: every item below is resolved, and this document now
describes the code that exists. Nothing was resolved by tuning a parameter.

### 1. D1's structural term was rebuilt (resolved, spec amended)

Revision 1.2's `1 + eta * max(0, r_dd - 1)` violated the specification's own
monotonicity guarantee. The factor decays as the mark ages, because `r_dd`'s
denominator grew with `sqrt(tau_stale)`, and on a high-dispersion asset it decayed
faster than the drift term accumulated: `sigma_U` fell from 35.6% at one day to
28.4% at seven before recovering — a staler mark reported as more reliable. Six
formulations were compared across five profiles:

| Variant | Worst peak-to-trough fall in `sigma_U` | Max inflation | Free parameter |
| --- | --- | --- | --- |
| 1.2 as written | 50.6% | 2.47x | `eta` |
| Freeze the window only | 0% | 2.47x | `eta` |
| Additive structural excess | 3.2% | 1.30x | `eta` |
| Delete the term, floor at `delta` | 0% | 1.00x | none |
| Withdraw the averaging credit | 1.8% | 1.25x | none |
| **Withdraw the credit, window fixed** | **0%** | **1.25x** | **none** |

The last was adopted and [D1](#d1-price-uncertainty) has been rewritten
accordingly; `eta` is deleted. Every variant leaves the headline frontier
identical, because its 5% dispersion sits below one-day diffusion — the choice
only moves assets whose sources disagree by more than their volatility explains.

### 1a. Frontier movement from the D1 change

Negligible, as predicted: R1 at 30% volatility moves from 28 to 27 days, and R3 at
80% from 30 to 17 days. Every margin figure in the headline table is unchanged to
one decimal place.

### 2. D5 was re-derived from first principles (resolved, spec amended)

Revision 1.2 paired `F_B = 1` with `f_B = phi_1 / x_ref`, which are not two facts
about the same distribution. Re-deriving from
`beta(x) = alpha * gamma * v^alpha * F_B(x)^(alpha-1) * f_B(x)` under an explicit
linear closure produced the collapsed form now in
[D5](#d5-concentration-and-cascade). Three forms — the general derivative at the
reference shock, the collapsed expression, and what the code computes — agree to a
relative `4e-16` across `alpha` in `[0.6, 1.8]`, `phi_1` in `[0.02, 0.20]`, and
two position sizes. **The implementation was mathematically correct; the document
was not**, so the document changed.

Consequences: the elasticity of `Q_max` to `phi_1` is exactly `-1` for every
`alpha`, and the `Q_max` table in D5 has been regenerated. Against revision 1.2's
form the cap is 1.48x larger at `alpha = 1.15` and 7.4x smaller at `alpha = 0.6`,
so the old formula was not uniformly conservative in either direction.

### 3. R2 reclassified as operational (resolved, spec amended)

`tau_u(q_max) = tau_u_max` identically, so R2 consults no market data at all.
Rather than repair it, the document now
[says what it is](#r2-is-an-operational-observability-constraint-not-a-risk-measurement):
a precondition on the venue's own operating model, sitting alongside the mechanism
question rather than among the risk dimensions. A market-derived alternative was
considered and rejected as duplicating R3. Behaviour unchanged.

### 4. The headline table is now reproducible (resolved)

The original table could not be reproduced, because the liquidity and jump
parameters behind it were never written down; only the `sigma_U` column, which
depends solely on recorded parameters, came out to the digit. The profile now
lives in `simulations/viability_frontier.py`, every headline figure in this
document and in `README.md` is regenerated from it, and margins came out roughly
8 points higher than the unrecorded original — enough to move R1 from 64 days to
27 at 30% volatility.

The qualitative finding is unchanged: parameters drift smoothly while the
mechanism holds, then stop existing.

### 5. Minor structural deviations from the module plan

* `v1/inputs.py` and `v1/params.py` were added; the plan gave the input model and
  the policy parameters no home.
* `RegimeTrigger` and `Mechanism` live in `regimes.py` rather than `outputs.py`,
  which would otherwise be a circular import. `outputs.py` re-exports them.
* `settlement_horizon_days` was added to policy to make `NOT_LISTABLE`
  decidable; the specification names the state but gives no test for it.
* `calibration/impact.py` was not created. The fitted constants are inlined in
  `v0_adapter.py` with their provenance, since nothing else consumes them yet.

---

## Out of scope for v1

Recorded so the boundary is deliberate rather than accidental.

- **Manipulation-resistant blended marks** (L1). A mark blending an external
  reference with the perp book could dominate either alone, but it requires a
  sixth dimension — manipulation resistance, scaling with perp book depth and
  the cost of moving it — plus an anchoring band and a policy for what happens
  when the band binds. v2.
- **Funding rate as an output.** A primary lever for an underlying that cannot be
  arbitraged.
- **Cross-market correlation** in concentration limits. Several private exposures
  of the same sector and vintage are close to one position.
- **Partial liquidations** and insurance fund dynamics.
- **The alternative mechanisms themselves.** v1 *names* a periodic auction or
  settled forward; it does not specify their collateral rules or cadence beyond
  `cadence >= tau_d`.

---

## Appendix A: review findings carried forward from revision 1.1

Retained because they justify design choices that would otherwise look arbitrary.

**Dimensional.** (D-1) Annualised `sigma` and `lambda` were multiplied by horizons
in days; at 120 days staleness this reported 1061% uncertainty instead of 55.6%.
(D-2) `q/D_eff` is a time once depth is a rate, requiring `T_ref`. (D-3) `gamma`
absorbs `sigma`; normalising narrows the cross-profile spread from 9.3x to 3.4x,
though partly mechanically. (D-5) A Pareto tail on simple returns violates limited
liability, hence log-space. (D-6) Timing risk needs the average-inventory `1/3`.

**Economic.** (E-1) `theta = 1 - sigma_basis^2/sigma^2` reaches -5.25 at
`sigma_basis/sigma = 2.5`, implying a bad hedge makes an asset harder to exit;
replaced by the bounded min-variance form. (E-2) The jump-implied leverage cap was
non-monotone in tail heaviness — at `lambda = 0.5`, a `xi = 1.5` tail permitted
50x against 32.9x for a thinner `xi = 4.0` tail — because the quantile was
evaluated outside the Pareto's domain. (E-3) The old regime condition reduced to
`sigma_U * (z_psi - kappa*z_phi) > kappa*(C + m_J)` and could never fire for
natural parameters. (E-4) Cascades liquidate directional, not net, open interest.
(E-5) Not every event improves liquidity. (E-6) Margin exceeding notional had no
defined behaviour, now resolved by L3 and R1.
