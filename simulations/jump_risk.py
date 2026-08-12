"""Does the recommended margin survive discontinuous repricing?

Illiquid underlyings do not drift; they jump. A private company can be flat for
a quarter and then reprice 30% on a single funding round, which means a
liquidation engine may never get to trade at the liquidation price. This
simulation prices that gap risk under a Merton jump-diffusion and compares the
resulting loss distribution to the margin the engine recommends.

Placeholder implementation. Future work: model the venue's actual liquidation
path (partial fills into finite depth) rather than marking the whole position at
the terminal price, and calibrate jump intensity to observed private-market
repricing frequency.

Run with::

    python -m simulations.jump_risk
"""

from __future__ import annotations

import numpy as np

from risk_engine import RiskInputs, evaluate_risk
from simulations import load_scenario

SCENARIO = "jump_risk"

# Calendar days, matching the v1 convention (docs/model_v1_spec.md, L4). All
# volatility and jump-intensity inputs are calendar-annualised.
CALENDAR_DAYS_PER_YEAR = 365.0


def simulate_terminal_returns(scenario: dict, rng: np.random.Generator) -> np.ndarray:
    """Simulate terminal log returns under a Merton jump-diffusion."""
    horizon_years = scenario["horizon_days"] / CALENDAR_DAYS_PER_YEAR
    n_paths = scenario["n_paths"]

    sigma = scenario["annual_volatility"]
    diffusion = rng.normal(
        loc=-0.5 * sigma**2 * horizon_years,
        scale=sigma * np.sqrt(horizon_years),
        size=n_paths,
    )

    n_jumps = rng.poisson(scenario["jump_intensity_per_year"] * horizon_years, size=n_paths)
    jump_totals = rng.normal(
        loc=scenario["jump_mean_log_return"] * n_jumps,
        scale=scenario["jump_volatility"] * np.sqrt(np.maximum(n_jumps, 0)),
    )

    return diffusion + jump_totals


def main() -> None:
    scenario = load_scenario(SCENARIO)
    rng = np.random.default_rng(scenario["seed"])

    inputs = RiskInputs(**scenario["inputs"])
    outputs = evaluate_risk(inputs)

    returns = np.exp(simulate_terminal_returns(scenario, rng)) - 1.0
    losses = -returns  # loss to a long position, as a fraction of notional

    im = outputs.initial_margin
    mm = outputs.maintenance_margin

    print(f"scenario: {scenario['description']}")
    print(f"paths: {scenario['n_paths']:,}   horizon: {scenario['horizon_days']} days\n")
    print(f"risk score          : {outputs.risk_score:6.2f}")
    print(f"initial margin      : {im:6.2%}")
    print(f"maintenance margin  : {mm:6.2%}")
    print(f"max leverage        : {outputs.recommended_max_leverage:6.1f}x\n")
    for q in (0.50, 0.90, 0.99, 0.999):
        print(f"loss quantile {q:6.1%} : {np.quantile(losses, q):6.2%}")
    print()
    print(f"P(loss > initial margin)     : {(losses > im).mean():6.2%}")
    print(f"P(loss > maintenance margin) : {(losses > mm).mean():6.2%}")


if __name__ == "__main__":
    main()
