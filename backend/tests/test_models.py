"""Validation behaviour of the shared input and output models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.tests.conftest import LIQUID_PUBLIC_ASSET
from risk_engine import RiskInputs


def test_valid_inputs_round_trip():
    inputs = RiskInputs(**LIQUID_PUBLIC_ASSET)
    assert inputs.model_dump() == pytest.approx(LIQUID_PUBLIC_ASSET)


@pytest.mark.parametrize(
    "field",
    [
        "liquidity_score",
        "oracle_confidence",
        "jump_risk",
        "hedgeability_score",
        "event_proximity",
    ],
)
def test_normalised_scores_reject_values_above_one(field):
    payload = {**LIQUID_PUBLIC_ASSET, field: 1.5}
    with pytest.raises(ValidationError):
        RiskInputs(**payload)


@pytest.mark.parametrize(
    "field",
    ["price_staleness_days", "oracle_dispersion", "current_open_interest", "market_depth"],
)
def test_unbounded_fields_reject_negative_values(field):
    payload = {**LIQUID_PUBLIC_ASSET, field: -1.0}
    with pytest.raises(ValidationError):
        RiskInputs(**payload)


def test_missing_field_is_rejected():
    payload = {k: v for k, v in LIQUID_PUBLIC_ASSET.items() if k != "market_depth"}
    with pytest.raises(ValidationError):
        RiskInputs(**payload)


def test_unknown_field_is_rejected():
    with pytest.raises(ValidationError):
        RiskInputs(**LIQUID_PUBLIC_ASSET, unexpected_field=1.0)
