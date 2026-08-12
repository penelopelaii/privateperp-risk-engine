# Data

Everything in this directory is **synthetic**. No proprietary, confidential, or
internal data of any kind belongs in this repository.

## Rules

1. Only synthetic or clearly-licensed public data may be committed.
2. Every file must state how it was generated or where it came from.
3. Names must be fictional. `SYNTH-PRIVATE-A` is acceptable; a real
   private-company name attached to invented valuation figures is not, because a
   fabricated number under a real name reads as a claim about that company.

## Contents

### `synthetic/asset_profiles.json`

Hand-written `RiskInputs` payloads spanning the liquidity spectrum, from a
deeply liquid public perp to a thinly traded private-company exposure. These are
the fixtures used by the frontend presets and by the docs when illustrating how
parameters change along that spectrum. The values are illustrative judgements,
not estimates of any real market.

#### Units of `market_depth`

`market_depth` is **USD per day**: the notional absorbable within an acceptable
slippage band over one day.

This matters because the v0 and v1 engines read the same field differently. v0
treats it as an undifferentiated stock of depth and only ever forms the ratio
`open_interest / market_depth`, so its units never surface. v1 uses it as a
**rate**, since the unwind horizon `tau_u = q / (rho_part * D_eff)` is only
dimensionally coherent if depth is a flow, and it converts to a dimensionless
"days of depth" via an explicit one-day reference period. See
[`docs/model_v1_spec.md`](../docs/model_v1_spec.md).

The numbers in this file are unchanged by that clarification; only their stated
meaning is now explicit. Time is calendar throughout, 365 days per year.

### `synthetic/depth_curves.csv`

Fabricated slippage curves: for each profile, the expected price impact of
executing a given notional. Used to sanity-check the `market_depth` input, which
compresses a whole curve into one number.
