"""Contract tests for ``POST /risk/v1/frontier``.

The frontier endpoint is a thin sweep over the same ``evaluate_v1`` path as
``/risk/v1/evaluate``. These tests pin that equivalence and the frozen grid
convention without requiring byte-identical JSON serialisation.
"""

from __future__ import annotations

import json
from pathlib import Path

from backend.app.services.risk_service import (
    FRONTIER_STALENESS_DAYS,
    FRONTIER_VOLATILITIES,
    evaluate_v1,
)
from risk_engine.v1 import MarketState

RECORDED_ILLIQUID = {
    "volatility": 0.9,
    "spot_depth": 350_000.0,
    "impact_exponent": 1.15,
    "impact_coefficient": 0.0703,
    "hedge_depth": 17_500.0,
    "hedge_volatility": 0.6,
    "hedge_correlation": 0.22,
    "hedge_ratio": 0.05,
    "mark_staleness_days": 30.0,
    "mark_refresh_days": 30.0,
    "source_count": 3,
    "source_dispersion": 0.05,
    "source_correlation": 0.5,
    "jump_intensity": 10.0,
    "jump_tail_index": 2.0,
    "jump_scale": 0.05,
    "open_interest_long": 5_000_000.0,
    "open_interest_short": 500_000.0,
    "crowding": {"low": 0.02, "high": 0.2},
}

GOLDEN = json.loads(
    (Path(__file__).resolve().parents[2] / "frontend" / "lib" / "frontierGrid.json").read_text()
)


def post_frontier(client, state, policy=None):
    body = {"state": state}
    if policy is not None:
        body["policy"] = policy
    return client.post("/risk/v1/frontier", json=body)


def test_frontier_grid_shape(client):
    payload = post_frontier(client, RECORDED_ILLIQUID).json()
    assert payload["evaluations"] == 304
    assert payload["staleness_days"] == list(FRONTIER_STALENESS_DAYS)
    assert payload["volatilities"] == list(FRONTIER_VOLATILITIES)
    assert len(payload["cells"]) == 304
    assert payload["engine_version"] == "1.0.0"


def test_frontier_matches_recorded_golden_grid(client):
    """With the recorded illiquid BASE, cells match the former baked scenario map."""
    cells = {
        (c["volatility"], c["staleness_days"]): c
        for c in post_frontier(client, RECORDED_ILLIQUID).json()["cells"]
    }
    for gold in GOLDEN["cells"]:
        key = (gold["volatility"], float(gold["staleness_days"]))
        got = cells[key]
        assert got["mechanism"] == gold["mechanism"]
        assert got["viable"] is gold["viable"]
        assert got["regimes"] == gold["regimes"]
        assert abs(got["initial_margin"] - gold["initial_margin"]) < 1e-6


def test_each_cell_matches_direct_evaluate_v1(client):
    """Categorical equality + float tolerance against a direct evaluate_v1 call."""
    sample = [(0.9, 0.0), (0.9, 5.0), (0.9, 120.0), (0.45, 21.0), (1.2, 3.0)]
    frontier = {
        (c["volatility"], c["staleness_days"]): c
        for c in post_frontier(client, RECORDED_ILLIQUID).json()["cells"]
    }
    for vol, days in sample:
        direct = evaluate_v1(
            MarketState(
                **{
                    **RECORDED_ILLIQUID,
                    "volatility": vol,
                    "mark_staleness_days": days,
                    "mark_refresh_days": max(days, 1.0),
                }
            )
        )
        cell = frontier[(vol, days)]
        assert cell["mechanism"] == direct.recommended_mechanism.value
        assert cell["viable"] is direct.viable_as_continuous_perp
        assert cell["regimes"] == [t.id.value for t in direct.triggered_regimes]
        assert (
            abs(
                cell["initial_margin"]
                - direct.margin_diagnostics.required_initial_margin
            )
            < 1e-9
        )


def test_non_axis_dispersion_moves_the_frontier(client):
    base = {
        (c["volatility"], c["staleness_days"]): c["mechanism"]
        for c in post_frontier(client, RECORDED_ILLIQUID).json()["cells"]
    }
    extreme = {
        (c["volatility"], c["staleness_days"]): c["mechanism"]
        for c in post_frontier(
            client, {**RECORDED_ILLIQUID, "source_dispersion": 0.20}
        ).json()["cells"]
    }
    assert base != extreme


def test_request_axis_fields_do_not_colour_the_map(client):
    """Different request vol/staleness must yield identical cell mechanisms."""
    a = post_frontier(
        client, {**RECORDED_ILLIQUID, "volatility": 0.3, "mark_staleness_days": 0}
    ).json()["cells"]
    b = post_frontier(
        client, {**RECORDED_ILLIQUID, "volatility": 1.2, "mark_staleness_days": 120}
    ).json()["cells"]
    assert [c["mechanism"] for c in a] == [c["mechanism"] for c in b]


def test_frontier_does_not_change_evaluate_contract(client):
    before = client.post(
        "/risk/v1/evaluate", json={"state": RECORDED_ILLIQUID}
    ).json()["outputs"]
    post_frontier(client, {**RECORDED_ILLIQUID, "source_dispersion": 0.20})
    after = client.post(
        "/risk/v1/evaluate", json={"state": RECORDED_ILLIQUID}
    ).json()["outputs"]
    assert after["recommended_mechanism"] == before["recommended_mechanism"]
    assert after["viable_as_continuous_perp"] is before["viable_as_continuous_perp"]
    assert after["triggered_regimes"] == before["triggered_regimes"]
    assert (
        abs(
            after["margin_diagnostics"]["required_initial_margin"]
            - before["margin_diagnostics"]["required_initial_margin"]
        )
        < 1e-12
    )
