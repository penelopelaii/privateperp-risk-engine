"""PrivatePerp risk engine, v0.

Pure domain logic with no web, file, or notebook dependencies. The single entry
point is :func:`evaluate_risk`, which maps one :class:`RiskInputs` to one
:class:`RiskOutputs`.

    >>> from risk_engine import RiskInputs, evaluate_risk
    >>> outputs = evaluate_risk(RiskInputs(**payload))

Every parameterisation at this level is a placeholder heuristic chosen for
explainability; see ``docs/assumptions.md`` for what that rules out. The
successor model lives in :mod:`risk_engine.v1` and shares none of this
machinery; ``risk_engine.v0_adapter`` bridges the two.
"""

from __future__ import annotations

from .inputs import RiskInputs, RiskOutputs
from .leverage import recommended_max_leverage
from .liquidation import liquidation_buffer
from .margin import initial_margin, maintenance_margin
from .open_interest import open_interest_cap, position_limit
from .oracle import oracle_reliability
from .risk_score import compute_risk_score, score_breakdown

ENGINE_VERSION = "0.1.0-placeholder"

__all__ = [
    "ENGINE_VERSION",
    "RiskInputs",
    "RiskOutputs",
    "evaluate_risk",
    "oracle_reliability",
]


def evaluate_risk(inputs: RiskInputs) -> RiskOutputs:
    """Evaluate a market and return its recommended risk parameters.

    The composite risk score is computed first and every other parameter is
    derived from it, so the engine stays monotonic: a strictly worse market
    never receives looser limits.
    """
    risk = compute_risk_score(inputs)
    im = initial_margin(risk)
    mm = maintenance_margin(risk)
    cap = open_interest_cap(inputs.market_depth, risk)

    return RiskOutputs(
        risk_score=risk,
        recommended_max_leverage=recommended_max_leverage(im),
        initial_margin=im,
        maintenance_margin=mm,
        position_limit=position_limit(cap, risk),
        open_interest_cap=cap,
        liquidation_buffer=liquidation_buffer(risk, inputs.jump_risk),
        score_breakdown=score_breakdown(inputs),
        engine_version=ENGINE_VERSION,
    )
