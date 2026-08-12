"""Regime preconditions and mechanism selection."""

from __future__ import annotations

from risk_engine.v1.regimes import Mechanism, RegimeId, evaluate_regimes, select_mechanism

HEALTHY = {
    "initial_margin": 0.20,
    "maintenance_margin": 0.12,
    "refresh_days": 1.0,
    "unwind_days": 5.0,
    "price_uncertainty": 0.01,
    "jump_loss_over_refresh": 0.01,
    "z_spurious": 2.0,
}


def test_healthy_market_trips_nothing():
    assert evaluate_regimes(**HEALTHY) == []


def test_r1_fires_when_margin_reaches_notional():
    triggered = evaluate_regimes(**{**HEALTHY, "initial_margin": 1.0})
    assert RegimeId.R1 in {t.id for t in triggered}


def test_r1_reports_the_unclamped_measurement():
    triggered = evaluate_regimes(**{**HEALTHY, "initial_margin": 2.675})
    r1 = next(t for t in triggered if t.id is RegimeId.R1)
    assert r1.measured == 2.675
    assert r1.threshold == 1.0


def test_r2_fires_when_the_mark_never_refreshes_during_an_unwind():
    triggered = evaluate_regimes(**{**HEALTHY, "refresh_days": 30.0, "unwind_days": 5.0})
    assert RegimeId.R2 in {t.id for t in triggered}


def test_r2_is_independent_of_margin_level():
    """No collateral schedule makes an unobservable state observable."""
    for margin in (0.05, 0.30, 0.95):
        triggered = evaluate_regimes(
            **{
                **HEALTHY,
                "initial_margin": margin,
                "maintenance_margin": margin / 2,
                "refresh_days": 30.0,
            }
        )
        assert RegimeId.R2 in {t.id for t in triggered}


def test_r3_fires_when_the_buffer_will_not_fit_in_the_cushion():
    triggered = evaluate_regimes(**{**HEALTHY, "price_uncertainty": 0.30})
    assert RegimeId.R3 in {t.id for t in triggered}


def test_r3_is_not_algebraically_dead():
    """Revision 1.0's condition could never fire for natural parameters.

    Sweeping price uncertainty must eventually trip R3 for any fixed cushion.
    """
    fired = [
        RegimeId.R3 in {t.id for t in evaluate_regimes(**{**HEALTHY, "price_uncertainty": u})}
        for u in (0.001, 0.01, 0.05, 0.20, 0.50)
    ]
    assert fired[0] is False
    assert fired[-1] is True


def test_mechanism_is_a_perp_when_nothing_trips():
    assert select_mechanism([], 1.0, 365.0) is Mechanism.CONTINUOUS_PERP


def test_r2_or_r3_alone_recommends_an_auction():
    """Decisions are unsound while collateral is adequate: change the cadence."""
    triggered = evaluate_regimes(**{**HEALTHY, "refresh_days": 30.0})
    assert select_mechanism(triggered, 30.0, 365.0) is Mechanism.PERIODIC_AUCTION


def test_r1_recommends_a_settled_forward():
    """Collateral has eliminated leverage: stop pretending it is leveraged."""
    triggered = evaluate_regimes(**{**HEALTHY, "initial_margin": 1.5})
    assert select_mechanism(triggered, 30.0, 365.0) is Mechanism.SETTLED_FORWARD


def test_nothing_is_listable_without_a_mark_inside_the_settlement_horizon():
    triggered = evaluate_regimes(**{**HEALTHY, "initial_margin": 1.5})
    assert select_mechanism(triggered, 500.0, 365.0) is Mechanism.NOT_LISTABLE
