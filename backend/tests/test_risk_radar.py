"""
Module C — Risk Radar Test Suite
=================================
Verifies:
1. Volatility computation: 14-day rolling annualized standard deviation and 7-day ROC.
2. Classification rule logic: Calm, Elevated, High threshold transitions and risk multiplier mapping.
3. HISTORICAL REPLAY BACKTEST DELIVERABLE:
   Replays the 4 curated RiskEvents from database and confirms 100% of events are flagged
   either concurrently or in advance.
4. RiskFlags database persistence and retrieval.
"""

from datetime import date
from decimal import Decimal
import pytest
import pandas as pd

from backend.app.database import SessionLocal
from backend.app.models import RiskEvent, RiskFlag, Route
from backend.app.services.risk_radar import (
    classify_risk_level,
    compute_market_volatility,
    evaluate_market_risk,
    replay_historical_risk_events,
)


@pytest.fixture(scope="function")
def db_session():
    """Function-scoped database session for risk radar tests with clean rollback."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_volatility_computation_structure(db_session):
    """Verify that compute_market_volatility returns valid non-negative metrics."""
    test_date = date(2023, 5, 10)
    vol = compute_market_volatility(eval_date=test_date, db=db_session)

    assert "sigma_ann_pct" in vol
    assert "roc_7_pct" in vol
    assert "price" in vol
    assert vol["price"] > 0
    assert vol["sigma_ann_pct"] >= 0.0


def test_risk_classification_thresholds():
    """Verify threshold boundary logic for CALM, ELEVATED, and HIGH."""
    # Case 1: Low vol, low ROC -> CALM
    level_calm, reason_calm = classify_risk_level(sigma_ann_pct=45.0, roc_7_pct=5.0)
    assert level_calm == "calm"
    assert "CALM" in reason_calm

    # Case 2: Elevated vol (65%) -> ELEVATED
    level_elev, reason_elev = classify_risk_level(sigma_ann_pct=65.0, roc_7_pct=8.0)
    assert level_elev == "elevated"
    assert "ELEVATED" in reason_elev

    # Case 3: High vol (90%) -> HIGH
    level_high, reason_high = classify_risk_level(sigma_ann_pct=90.0, roc_7_pct=10.0)
    assert level_high == "high"
    assert "HIGH" in reason_high

    # Case 4: High ROC (+22%) -> HIGH
    level_roc, reason_roc = classify_risk_level(sigma_ann_pct=50.0, roc_7_pct=22.0)
    assert level_roc == "high"
    assert "HIGH" in reason_roc


def test_replay_historical_risk_events_backtest_report(db_session):
    """
    CRITICAL DELIVERABLE:
    Replays the 4 curated RiskEvents from the database and confirms that the rule
    catches all 4 historical events (catch_rate == 100%).
    """
    df = replay_historical_risk_events(db=db_session)

    assert len(df) == 4, f"Expected 4 historical risk events, got {len(df)}"
    assert set(df["caught"].values) == {"YES"}, f"Not all events were caught: {df[['event_type', 'caught']]}"

    # Verify presence of all 4 canonical events
    event_types = set(df["event_type"].values)
    assert "Canal_Blockage" in event_types
    assert "Geopolitical" in event_types
    assert "Cyclone" in event_types
    assert "Port_Congestion" in event_types

    # Print the concrete backtest report for audit trail
    print("\n" + "=" * 80)
    print("HISTORICAL RISK RADAR BACKTEST REPORT (4/4 EVENTS FLAGGED)")
    print("=" * 80)
    cols = ["event_date", "event_type", "severity", "pre_vol_ann_pct", "concurrent_vol_ann_pct", "flagged_level", "caught", "detection_timing"]
    print(df[cols].to_string(index=False))
    print("=" * 80 + "\n")


def test_evaluate_market_risk_persistence(db_session):
    """Verify that evaluate_market_risk persists a RiskFlag row when persist_flag=True."""
    test_date = date(2023, 11, 20)  # Near Red Sea crisis onset
    res = evaluate_market_risk(eval_date=test_date, db=db_session, persist_flag=True)

    assert res["risk_level"] in ("elevated", "high")
    assert res["risk_multiplier"] in (1.15, 1.50)
    assert res["flag_id"] is not None

    # Query DB to verify persistence
    flag = db_session.query(RiskFlag).filter(RiskFlag.flag_id == res["flag_id"]).first()
    assert flag is not None
    assert flag.risk_level == res["risk_level"]
    assert flag.is_active is True
