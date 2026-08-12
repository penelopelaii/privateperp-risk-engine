"""Adapter between the HTTP layer and the risk engine.

Kept deliberately thin: anything that looks like risk logic belongs in
``risk_engine`` so it can be exercised from simulations and notebooks without a
running server.
"""

from __future__ import annotations

from risk_engine import evaluate_risk
from risk_engine.inputs import RiskInputs, RiskOutputs
from risk_engine.v1 import (
    MarketState,
    PolicyParameters,
    Provenance,
    RiskOutputsV1,
    evaluate_risk_v1,
)
from risk_engine.v1.provenance import uniform


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
