"""Do liquidations at these limits become self-reinforcing?

Liquidating into a thin book moves the price, which pushes more accounts below
maintenance margin, which liquidates more size. On a deep market this feedback
dies out immediately; the question is whether the open interest cap the engine
recommends is low enough that it still dies out when depth is small.

Placeholder implementation: a round-based model where each round's liquidated
notional produces price impact proportional to ``(size / depth) ** exponent``,
and the resulting price move is re-applied to the surviving accounts.

Future work: replace the uniform leverage assumption with a realistic
distribution of account leverage, and model partial liquidations and
insurance-fund absorption rather than closing whole positions.

Run with::

    python -m simulations.liquidation_cascade
"""

from __future__ import annotations

import numpy as np

from risk_engine import RiskInputs, evaluate_risk
from simulations import load_scenario

SCENARIO = "liquidation_cascade"


def run_cascade(
    account_notional: np.ndarray,
    account_equity: np.ndarray,
    scenario: dict,
    maintenance_margin: float,
) -> tuple[float, float, int]:
    """Run one cascade to exhaustion.

    Returns the fraction of open interest liquidated, the total price move, and
    the number of rounds it took to settle.
    """
    alive = np.ones_like(account_notional, dtype=bool)
    cumulative_move = scenario["shock_log_return"]
    account_equity = account_equity + account_notional * scenario["shock_log_return"]

    liquidated_notional = 0.0
    for round_index in range(1, scenario["max_rounds"] + 1):
        underwater = alive & (account_equity < account_notional * maintenance_margin)
        if not underwater.any():
            return liquidated_notional / account_notional.sum(), cumulative_move, round_index

        forced = account_notional[underwater].sum()
        liquidated_notional += forced
        alive &= ~underwater

        impact = -((forced / scenario["market_depth"]) ** scenario["price_impact_exponent"]) * 0.01
        cumulative_move += impact
        account_equity = account_equity + account_notional * impact

    return liquidated_notional / account_notional.sum(), cumulative_move, scenario["max_rounds"]


def main() -> None:
    scenario = load_scenario(SCENARIO)
    rng = np.random.default_rng(scenario["seed"])

    inputs = RiskInputs(**scenario["inputs"])
    outputs = evaluate_risk(inputs)

    n_accounts = scenario["n_accounts"]

    print(f"scenario: {scenario['description']}")
    print(f"accounts: {n_accounts}   shock: {scenario['shock_log_return']:.0%}")
    print(f"recommended OI cap: ${outputs.open_interest_cap:,.0f}")
    print(f"maintenance margin: {outputs.maintenance_margin:.2%}\n")
    print(f"{'open interest':>16} {'liquidated':>12} {'price move':>12} {'rounds':>8}")

    for oi_multiple in (0.5, 1.0, 2.0, 4.0):
        open_interest = outputs.open_interest_cap * oi_multiple
        notional = np.full(n_accounts, open_interest / n_accounts)
        # Accounts open at initial margin or above, spread over a range of
        # collateralisation up to three times the minimum.
        equity = notional * rng.uniform(
            outputs.initial_margin, 3.0 * outputs.initial_margin, size=n_accounts
        )

        fraction, move, rounds = run_cascade(
            notional, equity, scenario, outputs.maintenance_margin
        )
        print(f"{open_interest:>15,.0f} {fraction:>11.1%} {move:>11.1%} {rounds:>8}")

    print(
        "\nA cascade that settles in one round is contained; one that keeps liquidating "
        "as open interest grows is the case the cap exists to prevent."
    )


if __name__ == "__main__":
    main()
