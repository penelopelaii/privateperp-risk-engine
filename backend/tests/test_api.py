"""API contract tests."""

from __future__ import annotations

from backend.tests.conftest import ILLIQUID_PRIVATE_EXPOSURE


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["api_version"]
    assert body["engine_version"]


def test_evaluate_returns_all_risk_parameters(client):
    response = client.post("/risk/evaluate", json={"inputs": ILLIQUID_PRIVATE_EXPOSURE})
    assert response.status_code == 200

    outputs = response.json()["outputs"]
    expected = {
        "risk_score",
        "recommended_max_leverage",
        "initial_margin",
        "maintenance_margin",
        "position_limit",
        "open_interest_cap",
        "liquidation_buffer",
        "score_breakdown",
        "engine_version",
    }
    assert set(outputs) == expected


def test_evaluate_echoes_inputs(client):
    response = client.post("/risk/evaluate", json={"inputs": ILLIQUID_PRIVATE_EXPOSURE})
    assert response.json()["inputs"] == ILLIQUID_PRIVATE_EXPOSURE


def test_evaluate_rejects_out_of_range_input(client):
    payload = {**ILLIQUID_PRIVATE_EXPOSURE, "liquidity_score": 42.0}
    response = client.post("/risk/evaluate", json={"inputs": payload})
    assert response.status_code == 422
