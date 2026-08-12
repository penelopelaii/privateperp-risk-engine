from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from risk_engine import RiskInputs

LIQUID_PUBLIC_ASSET = {
    "liquidity_score": 0.95,
    "oracle_confidence": 0.98,
    "price_staleness_days": 0.0,
    "oracle_dispersion": 0.001,
    "jump_risk": 0.1,
    "hedgeability_score": 0.95,
    "event_proximity": 0.0,
    "current_open_interest": 25_000_000.0,
    "market_depth": 20_000_000.0,
}

ILLIQUID_PRIVATE_EXPOSURE = {
    "liquidity_score": 0.1,
    "oracle_confidence": 0.3,
    "price_staleness_days": 120.0,
    "oracle_dispersion": 0.18,
    "jump_risk": 0.85,
    "hedgeability_score": 0.05,
    "event_proximity": 0.7,
    "current_open_interest": 5_000_000.0,
    "market_depth": 400_000.0,
}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def liquid_inputs() -> RiskInputs:
    return RiskInputs(**LIQUID_PUBLIC_ASSET)


@pytest.fixture
def illiquid_inputs() -> RiskInputs:
    return RiskInputs(**ILLIQUID_PRIVATE_EXPOSURE)
