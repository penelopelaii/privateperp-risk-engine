"""Where does continuous mark-based margining stop working?

Sweeps mark staleness and volatility over an otherwise fixed illiquid profile and
reports the point at which each precondition fails. Reproduces the headline
finding of ``docs/model_v1_spec.md``.

Run with:

    python -m simulations.viability_frontier
"""

from __future__ import annotations

from risk_engine.v1 import DEFAULT_POLICY, Interval, MarketState, evaluate_risk_v1
from risk_engine.v1.regimes import RegimeId

# One illiquid profile, held fixed while staleness and volatility vary. The 5%
# source dispersion is the assumption doing the most work at low volatility: it
# is noise on a 120% asset and a structural pricing failure on a 30% one.
BASE = {
    "spot_depth": 350_000.0,
    "impact_exponent": 1.15,
    "impact_coefficient": 0.0703,
    "hedge_depth": 17_500.0,
    "hedge_volatility": 0.60,
    "hedge_correlation": 0.22,
    "hedge_ratio": 0.05,
    "source_count": 3,
    "source_dispersion": 0.05,
    "source_correlation": 0.5,
    "jump_intensity": 10.0,
    "jump_tail_index": 2.0,
    "jump_scale": 0.05,
    "open_interest_long": 5_000_000.0,
    "open_interest_short": 500_000.0,
    "crowding": Interval(low=0.02, high=0.20),
}

STALENESS_GRID = (0.0, 1.0, 7.0, 14.0, 30.0, 120.0)
VOLATILITY_GRID = (0.30, 0.50, 0.80, 1.00, 1.20)
HEADLINE_VOLATILITY = 0.90


def state_at(volatility: float, staleness: float) -> MarketState:
    return MarketState(
        volatility=volatility,
        mark_staleness_days=staleness,
        mark_refresh_days=max(staleness, 1.0),
        **BASE,
    )


def first_trip(regime: RegimeId, volatility: float, limit_days: int = 400) -> int | None:
    """Smallest whole day of staleness at which ``regime`` fires."""
    for day in range(limit_days + 1):
        outputs = evaluate_risk_v1(state_at(volatility, float(day)), DEFAULT_POLICY)
        if regime in {trigger.id for trigger in outputs.triggered_regimes}:
            return day
    return None


def degradation_table() -> None:
    print(f"Illiquid profile at {HEADLINE_VOLATILITY:.0%} annualised volatility\n")
    print(f"{'staleness':>10}  {'sigma_U':>8}  {'maint':>8}  {'initial':>8}  {'leverage':>9}  status")
    for staleness in STALENESS_GRID:
        outputs = evaluate_risk_v1(state_at(HEADLINE_VOLATILITY, staleness), DEFAULT_POLICY)
        diagnostics = outputs.margin_diagnostics
        leverage = f"{outputs.tradable.max_leverage:.2f}x" if outputs.tradable else "-"
        if outputs.viable_as_continuous_perp:
            status = "viable"
        else:
            status = "NOT VIABLE (" + ", ".join(
                t.id.value for t in outputs.triggered_regimes
            ) + ") -> " + outputs.recommended_mechanism.value
        print(
            f"{staleness:>9.0f}d  {outputs.dimensions.price_uncertainty:>7.1%}  "
            f"{diagnostics.required_maintenance_margin:>7.1%}  "
            f"{diagnostics.required_initial_margin:>7.1%}  {leverage:>9}  {status}"
        )


def frontier_table() -> None:
    print("\nFirst day of staleness at which each precondition fails\n")
    print(f"{'sigma':>6}  {'R3 (trigger)':>13}  {'R1 (solvency)':>14}  {'R2 (feedback)':>14}")
    for volatility in VOLATILITY_GRID:
        cells = []
        for regime in (RegimeId.R3, RegimeId.R1, RegimeId.R2):
            day = first_trip(regime, volatility)
            cells.append("never" if day is None else f"{day}d")
        print(f"{volatility:>5.0%}  {cells[0]:>13}  {cells[1]:>14}  {cells[2]:>14}")


def main() -> None:
    degradation_table()
    frontier_table()
    print(
        "\nParameters drift smoothly while the mechanism holds, and then stop existing."
    )


if __name__ == "__main__":
    main()
