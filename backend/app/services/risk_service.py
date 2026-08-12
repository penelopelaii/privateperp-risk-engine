"""Adapter between the HTTP layer and the risk engine.

Kept deliberately thin: anything that looks like risk logic belongs in
``risk_engine`` so it can be exercised from simulations and notebooks without a
running server.
"""

from __future__ import annotations

from backend.app.models.schemas import FrontierCellV1, FrontierV1Response
from risk_engine import evaluate_risk
from risk_engine.inputs import RiskInputs, RiskOutputs
from risk_engine.v1 import (
    ENGINE_VERSION,
    MarketState,
    PolicyParameters,
    Provenance,
    RiskOutputsV1,
    evaluate_risk_v1,
)
from risk_engine.v1.provenance import uniform

# Same axes as the recorded scenario map / former frontierGrid.json — frozen
# research convention for this endpoint.
FRONTIER_STALENESS_DAYS: tuple[float, ...] = (
    0.0,
    1.0,
    2.0,
    3.0,
    4.0,
    5.0,
    6.0,
    7.0,
    10.0,
    14.0,
    21.0,
    30.0,
    45.0,
    60.0,
    90.0,
    120.0,
)
FRONTIER_VOLATILITIES: tuple[float, ...] = tuple(
    round(0.30 + 0.05 * i, 2) for i in range(19)
)


def evaluate(inputs: RiskInputs) -> RiskOutputs:
    """Run a single v0 risk evaluation."""
    return evaluate_risk(inputs)


def evaluate_v1(
    state: MarketState, params: PolicyParameters | None = None
) -> RiskOutputsV1:
    """Run a single v1 risk evaluation.

    Every field of a state that arrived over HTTP is tagged ``ASSUMED``. Nothing
    reaching this function from a slider or a scenario file is a measurement, and
    the provenance contract exists precisely so that the output cannot imply
    otherwise. A caller with genuinely measured inputs should invoke
    ``evaluate_risk_v1`` directly and supply its own provenance map.
    """
    supplied = uniform(type(state).model_fields.keys(), Provenance.ASSUMED)
    return evaluate_risk_v1(state, params, input_provenance=supplied)


def evaluate_frontier_v1(
    state: MarketState, params: PolicyParameters | None = None
) -> FrontierV1Response:
    """Sweep (staleness × volatility) holding all other fields of ``state`` fixed.

    Each cell is a normal ``evaluate_v1`` call. Axis fields on the request are
    overwritten per cell; ``mark_refresh_days = max(staleness, 1)`` matches the
    frozen research convention. No new risk formulas live here.
    """
    cells: list[FrontierCellV1] = []
    for volatility in FRONTIER_VOLATILITIES:
        for staleness in FRONTIER_STALENESS_DAYS:
            cell_state = state.model_copy(
                update={
                    "volatility": volatility,
                    "mark_staleness_days": staleness,
                    "mark_refresh_days": max(staleness, 1.0),
                }
            )
            outputs = evaluate_v1(cell_state, params)
            cells.append(
                FrontierCellV1(
                    volatility=volatility,
                    staleness_days=staleness,
                    mechanism=outputs.recommended_mechanism,
                    viable=outputs.viable_as_continuous_perp,
                    initial_margin=outputs.margin_diagnostics.required_initial_margin,
                    regimes=[trigger.id for trigger in outputs.triggered_regimes],
                )
            )

    return FrontierV1Response(
        staleness_days=list(FRONTIER_STALENESS_DAYS),
        volatilities=list(FRONTIER_VOLATILITIES),
        cells=cells,
        evaluations=len(cells),
        engine_version=ENGINE_VERSION,
    )
