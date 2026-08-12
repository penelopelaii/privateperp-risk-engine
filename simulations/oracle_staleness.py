"""How wrong is the mark we liquidate against?

A perp enforces margin against an oracle price. When that price only refreshes
every few weeks, the venue is making solvency decisions on a number that has
drifted from reality. This simulation measures the error between a stale mark
and the true price at various refresh intervals, which is the quantity the
liquidation buffer has to absorb.

Placeholder implementation. Future work: add source dispersion (an ensemble of
noisy marks rather than one lagged mark) and measure liquidation *timing* error
in addition to price error.

Run with::

    python -m simulations.oracle_staleness
"""

from __future__ import annotations

import numpy as np

from risk_engine import RiskInputs, evaluate_risk
from simulations import load_scenario

SCENARIO = "oracle_staleness"

# Calendar days, matching the v1 convention (docs/model_v1_spec.md, L4). All
# volatility and jump-intensity inputs are calendar-annualised.
CALENDAR_DAYS_PER_YEAR = 365.0


def simulate_price_paths(scenario: dict, rng: np.random.Generator) -> np.ndarray:
    """Return geometric Brownian motion paths of shape (n_paths, horizon_days + 1)."""
    sigma = scenario["annual_volatility"]
    dt = 1.0 / CALENDAR_DAYS_PER_YEAR
    steps = rng.normal(
        loc=-0.5 * sigma**2 * dt,
        scale=sigma * np.sqrt(dt),
        size=(scenario["n_paths"], scenario["horizon_days"]),
    )
    log_paths = np.concatenate(
        [np.zeros((scenario["n_paths"], 1)), np.cumsum(steps, axis=1)], axis=1
    )
    return np.exp(log_paths)


def stale_marks(paths: np.ndarray, refresh_interval_days: int) -> np.ndarray:
    """Return the most recent refreshed mark for each day of each path."""
    days = np.arange(paths.shape[1])
    last_refresh = (days // refresh_interval_days) * refresh_interval_days
    return paths[:, last_refresh]


def main() -> None:
    scenario = load_scenario(SCENARIO)
    rng = np.random.default_rng(scenario["seed"])

    paths = simulate_price_paths(scenario, rng)

    print(f"scenario: {scenario['description']}")
    print(f"paths: {scenario['n_paths']:,}   horizon: {scenario['horizon_days']} days\n")
    print(f"{'refresh':>9} {'median err':>12} {'p95 err':>10} {'buffer':>9}")

    for interval in scenario["refresh_interval_days"]:
        error = np.abs(stale_marks(paths, interval) / paths - 1.0)

        inputs = RiskInputs(**{**scenario["inputs"], "price_staleness_days": float(interval)})
        outputs = evaluate_risk(inputs)
        # Buffer is a fraction of maintenance margin; express it in price terms
        # so it is comparable to the mark error.
        buffer_in_price = outputs.maintenance_margin * outputs.liquidation_buffer

        print(
            f"{interval:>8}d {np.median(error):>11.2%} "
            f"{np.quantile(error, 0.95):>9.2%} {buffer_in_price:>8.2%}"
        )

    print(
        "\nWhere p95 mark error exceeds the buffer, the venue is liquidating on a "
        "price it cannot defend."
    )


if __name__ == "__main__":
    main()
