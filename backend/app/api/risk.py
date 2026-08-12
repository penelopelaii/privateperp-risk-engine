"""Risk evaluation endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.models import (
    FrontierV1Request,
    FrontierV1Response,
    RiskEvaluationRequest,
    RiskEvaluationResponse,
    RiskEvaluationV1Request,
    RiskEvaluationV1Response,
)
from backend.app.services import evaluate, evaluate_frontier_v1, evaluate_v1
from risk_engine.v1 import DEFAULT_POLICY

router = APIRouter(prefix="/risk", tags=["risk"])


@router.post("/evaluate", response_model=RiskEvaluationResponse)
def evaluate_market(request: RiskEvaluationRequest) -> RiskEvaluationResponse:
    """Return recommended risk parameters for a described market state.

    The v0 composite-score engine. Frozen: this endpoint's request and response
    shapes will not change, and `test_api.py` pins its output.

    The request is echoed back alongside the outputs so a stored response is a
    self-contained record of what produced a given recommendation.
    """
    return RiskEvaluationResponse(inputs=request.inputs, outputs=evaluate(request.inputs))


@router.post("/v1/evaluate", response_model=RiskEvaluationV1Response)
def evaluate_market_v1(request: RiskEvaluationV1Request) -> RiskEvaluationV1Response:
    """Return a v1 risk assessment for a described market state.

    Unlike v0, this endpoint may answer that no set of parameters works. When
    `viable_as_continuous_perp` is false, `tradable` is null and the caller is
    expected to read `recommended_mechanism` instead of reaching for a leverage
    number. The unconstrained margin requirement is always present in
    `margin_diagnostics`, unclamped, even above 100% of notional.

    The resolved policy is echoed back alongside the state, so a stored response
    records both halves of what produced the recommendation: the market, and the
    venue's own risk appetite.
    """
    policy = request.policy or DEFAULT_POLICY
    return RiskEvaluationV1Response(
        state=request.state,
        policy=policy,
        outputs=evaluate_v1(request.state, policy),
    )


@router.post("/v1/frontier", response_model=FrontierV1Response)
def evaluate_frontier(request: FrontierV1Request) -> FrontierV1Response:
    """Sweep the viability map for the current non-axis market state.

    Holds every field of ``state`` fixed except the swept axes. Each cell is a
    normal v1 evaluation — the same path as ``/risk/v1/evaluate``. Request axis
    fields are overwritten per cell; see ``evaluate_frontier_v1``.
    """
    policy = request.policy or DEFAULT_POLICY
    return evaluate_frontier_v1(request.state, policy)
