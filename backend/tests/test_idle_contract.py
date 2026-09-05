"""
Module E — Idle-Time & Contract Structuring Test Suite
======================================================
Verifies:
1. Exact mathematical trough-detection logic (trailing 20th percentile, contiguous window scan).
2. Exact speed and fuel physics equations (T_required, v_recommended clamping, Fuel_ref, CO2, Cost).
3. Conditional trigger: JIT advisory executes strictly when vessel_in_transit=True.
4. Independent Challenge 10 Sanity Guardrails on E1 and E2 (halting on savings > 25.0%).
5. Reusable consolidated backtest engine (ml/backtest.py) and summary report generation.
6. Database persistence of IdleTimeAnalysis and SpeedOptimizationLog records.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from backend.app.database import SessionLocal
from backend.app.models import (
    CargoRequest,
    IdleTimeAnalysis,
    Port,
    Route,
    SpeedOptimizationLog,
    VesselType,
)
from backend.app.services.idle_contract import (
    DEFAULT_BUNKER_FUEL_PRICE_USD_PER_TON,
    DEFAULT_PORT_CONGESTION_HOURS,
    DEFAULT_SAFETY_BUFFER_HOURS,
    DEFAULT_TROUGH_WINDOW_DAYS,
    IMO_VLSFO_CO2_FACTOR_KG_PER_TON,
    MAX_PLAUSIBLE_SAVING_PCT,
    MIN_SAFE_SPEED_KNOTS,
    calculate_speed_and_fuel_optimization,
    calculate_trailing_percentile,
    detect_market_trough,
    evaluate_idle_contract_for_request,
)
from ml.backtest import (
    Challenge10SanityViolation,
    generate_unified_backtest_report,
    run_decision_backtest,
    run_idle_time_backtest,
    run_speed_backtest,
    verify_challenge_10_guardrail,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="function")
def db_session():
    """Function-scoped database session with clean rollback."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# =============================================================================
# 1. MODULE E1: TROUGH DETECTION UNIT TESTS
# =============================================================================

def test_trailing_percentile_calculation():
    """Verify trailing 20th percentile computation enforces zero lookahead."""
    # Synthetic prices: 10, 20, 30, 40, 50
    prices = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    p20 = calculate_trailing_percentile(prices, percentile=20.0)
    # 20th percentile of [10, 20, 30, 40, 50] is 18.0
    assert p20 == pytest.approx(18.0, abs=0.1)


def test_trough_detection_period_vs_spot():
    """
    Verify detect_market_trough recommends 'period' when a contiguous window >= 14 days
    is at or below the trailing 20th percentile, and 'spot' otherwise.
    """
    eval_d = date(2023, 5, 1)
    # 300 days of historical prices averaging ~25.0, 20th percentile ~15.0
    np.random.seed(42)
    hist_prices = pd.Series(np.random.uniform(14.0, 35.0, size=300))
    p20 = float(np.percentile(hist_prices, 20.0))

    # Case A: 14 consecutive days below p20 -> PERIOD
    forecast_curve_trough = [
        {"horizon_days": i, "target_date": f"2023-05-{i:02d}", "p50_price": p20 - 1.0}
        for i in range(1, 15)
    ]
    res_period = detect_market_trough(
        forecast_curve=forecast_curve_trough,
        historical_prices=hist_prices,
        eval_date=eval_d,
        trough_window_days=14,
    )
    assert res_period["trough_detected"] is True
    assert res_period["recommended_contract_type"] == "period"
    assert res_period["contiguous_trough_days_found"] == 14
    assert res_period["forecasted_trough_start"] == "2023-05-01"
    assert res_period["forecasted_trough_end"] == "2023-05-14"
    assert res_period["estimated_cost_saved_usd"] > 0

    # Case B: High prices above p20 -> SPOT
    forecast_curve_high = [
        {"horizon_days": i, "target_date": f"2023-05-{i:02d}", "p50_price": p20 + 5.0}
        for i in range(1, 15)
    ]
    res_spot = detect_market_trough(
        forecast_curve=forecast_curve_high,
        historical_prices=hist_prices,
        eval_date=eval_d,
        trough_window_days=14,
    )
    assert res_spot["trough_detected"] is False
    assert res_spot["recommended_contract_type"] == "spot"
    assert res_spot["forecasted_trough_start"] is None
    assert res_spot["forecasted_trough_end"] is None
    assert res_spot["estimated_cost_saved_usd"] == 0.0

    # Case C: Interrupted trough (only 8 contiguous days below p20, then price spikes) -> SPOT
    interrupted_curve = [
        {"horizon_days": i, "target_date": f"2023-05-{i:02d}", "p50_price": p20 - 1.0 if i <= 8 else p20 + 3.0}
        for i in range(1, 15)
    ]
    res_interrupted = detect_market_trough(
        forecast_curve=interrupted_curve,
        historical_prices=hist_prices,
        eval_date=eval_d,
        trough_window_days=14,
    )
    assert res_interrupted["trough_detected"] is False
    assert res_interrupted["recommended_contract_type"] == "spot"
    assert res_interrupted["contiguous_trough_days_found"] == 8


# =============================================================================
# 2. MODULE E2: SPEED & FUEL PHYSICS FORMULAS
# =============================================================================

def test_speed_and_fuel_physics_exact_arithmetic():
    """
    Verify Module E2 formulas against hand-computed values:
    d = 1000 nm, v_std = 14.0 knots, fuel_coef = 0.0164 (Capesize)
    Congestion = 36.0h, buffer = 4.0h -> net delay = 32.0h
    T_std = 1000 / 14.0 = 71.43h
    T_required = 71.43 + 32.0 = 103.43h
    v_target = 1000 / 103.43 = 9.67 knots -> clamped to min_safe_speed = 10.0 knots!
    """
    d = 1000.0
    v_std = 14.0
    fuel_coef = 0.0164
    congestion = 36.0
    buffer = 4.0

    res = calculate_speed_and_fuel_optimization(
        distance_remaining_nm=d,
        standard_speed_knots=v_std,
        fuel_curve_coef=fuel_coef,
        expected_port_congestion_hours=congestion,
        safety_buffer_hours=buffer,
        min_safe_speed_knots=10.0,
        emission_factor_kg_per_unit=3114.0,
        bunker_fuel_price_usd_per_unit=600.0,
    )

    # 1. Clamping check: target 9.67 kts clamped to 10.0 kts
    assert res["standard_speed_knots"] == 14.0
    assert res["recommended_speed_knots"] == 10.0
    assert res["speed_reduction_knots"] == 4.0

    # 2. Fuel consumption check (Admiralty passage equation: (c / 24) * d * v^2):
    # Fuel_std = (0.0164 / 24) * 1000 * (14^2) = 3214.4 / 24 = 133.93 tons
    # Fuel_rec = (0.0164 / 24) * 1000 * (10^2) = 1640.0 / 24 = 68.33 tons
    # Fuel_saved = 133.93 - 68.33 = 65.60 tons
    assert res["fuel_standard_tons"] == pytest.approx(133.93, abs=0.1)
    assert res["fuel_recommended_tons"] == pytest.approx(68.33, abs=0.1)
    assert res["fuel_saved_tons"] == pytest.approx(65.60, abs=0.1)

    # 3. Environmental & Economic savings:
    # CO2 = 65.60 * 3114.0 = 204,278.4 kg
    # Cost = 65.60 * 600.0 = $39,360.00
    assert res["co2_reduced_kg"] == pytest.approx(65.60 * 3114.0, abs=10.0)
    assert res["cost_saved_usd"] == pytest.approx(65.60 * 600.0, abs=10.0)


def test_speed_optimization_zero_congestion():
    """When destination port has 0 congestion, recommended speed equals standard speed."""
    res_zero = calculate_speed_and_fuel_optimization(
        distance_remaining_nm=1000.0,
        standard_speed_knots=14.0,
        fuel_curve_coef=0.0164,
        expected_port_congestion_hours=0.0,
        safety_buffer_hours=4.0,
    )
    assert res_zero["recommended_speed_knots"] == 14.0
    assert res_zero["fuel_saved_tons"] == 0.0
    assert res_zero["co2_reduced_kg"] == 0.0
    assert res_zero["cost_saved_usd"] == 0.0


# =============================================================================
# 3. CONDITIONAL TRIGGER & DATABASE PERSISTENCE
# =============================================================================

def test_conditional_trigger_and_database_persistence(db_session):
    """
    Verify:
    1. vessel_in_transit=False -> E2 not applicable, no SpeedOptimizationLog created.
    2. vessel_in_transit=True -> E2 computes advisory and creates SpeedOptimizationLog.
    3. IdleTimeAnalysis row is persisted in both cases.
    """
    origin = db_session.query(Port).filter(Port.name == "Taboneo").first()
    dest = db_session.query(Port).filter(Port.name == "Paradip_Inner").first()
    assert origin is not None and dest is not None

    req = CargoRequest(
        cargo_type="coking_coal",
        cargo_volume_tons=55000,
        origin_port_id=origin.port_id,
        destination_port_id=dest.port_id,
        desired_timeframe_days=30,
        desired_contract_pref="spot",
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)

    # Test 1: Vessel NOT in transit
    res_not_transit = evaluate_idle_contract_for_request(
        request=req,
        db=db_session,
        eval_date=date(2023, 6, 1),
        vessel_in_transit=False,
        persist_records=True,
    )
    assert res_not_transit["speed_and_fuel_advisory"]["applicable"] is False
    assert res_not_transit["spot_vs_period"]["analysis_id"] is not None

    # Verify IdleTimeAnalysis exists in DB
    persisted_idle = db_session.query(IdleTimeAnalysis).filter(
        IdleTimeAnalysis.analysis_id == res_not_transit["spot_vs_period"]["analysis_id"]
    ).first()
    assert persisted_idle is not None
    assert persisted_idle.recommended_contract_type in ("spot", "period")

    # Verify NO SpeedOptimizationLog exists for this request
    count_speed = db_session.query(SpeedOptimizationLog).filter(
        SpeedOptimizationLog.request_id == req.request_id
    ).count()
    assert count_speed == 0

    # Test 2: Vessel IN transit
    res_transit = evaluate_idle_contract_for_request(
        request=req,
        db=db_session,
        eval_date=date(2023, 6, 1),
        vessel_in_transit=True,
        distance_remaining_nm=1000.0,
        expected_port_congestion_hours=36.0,
        persist_records=True,
    )
    assert res_transit["speed_and_fuel_advisory"]["applicable"] is True
    assert res_transit["speed_and_fuel_advisory"]["speed_id"] is not None
    assert res_transit["speed_and_fuel_advisory"]["fuel_saved_tons"] > 0

    # Verify SpeedOptimizationLog exists in DB
    persisted_speed = db_session.query(SpeedOptimizationLog).filter(
        SpeedOptimizationLog.speed_id == res_transit["speed_and_fuel_advisory"]["speed_id"]
    ).first()
    assert persisted_speed is not None
    assert float(persisted_speed.standard_speed_knots) > 0
    assert float(persisted_speed.recommended_speed_knots) > 0
    assert float(persisted_speed.fuel_saved_tons) > 0


# =============================================================================
# 4. INDEPENDENT CHALLENGE 10 SANITY CHECKS & CONSOLIDATED BACKTEST
# =============================================================================

def test_challenge_10_guardrail_independent_rejection():
    """Verify Challenge 10 guardrail rejects savings > 25.0% for any module."""
    # Saving within bounds -> passes
    verify_challenge_10_guardrail("TestModule", 18.5)

    # Saving exceeding bounds -> raises Challenge10SanityViolation
    with pytest.raises(Challenge10SanityViolation):
        verify_challenge_10_guardrail("TestModule", 28.5)


def test_consolidated_backtest_execution(db_session):
    """
    CRITICAL DELIVERABLE:
    Executes all three backtests via ml/backtest.py and verifies:
    1. Module D Decision Engine aggregate savings <= 25.0%.
    2. Module E1 Idle-Time aggregate savings <= 25.0%.
    3. Module E2 Speed & Fuel portfolio fuel reduction <= 25.0%.
    4. Comprehensive summary report is written to reports/backtest_summary.md.
    """
    report = generate_unified_backtest_report(db=db_session)

    # 1. Module D assertions
    d_res = report["module_d"]
    assert d_res["fixture_count"] == 25
    assert d_res["aggregate_saving_pct"] <= MAX_PLAUSIBLE_SAVING_PCT
    assert d_res["challenge_10_passed"] is True

    # 2. Module E1 assertions
    e1_res = report["module_e1"]
    assert e1_res["fixture_count"] == 25
    assert e1_res["aggregate_cost_saved_pct"] <= MAX_PLAUSIBLE_SAVING_PCT
    assert e1_res["total_idle_days_avoided"] >= 0.0
    assert e1_res["challenge_10_passed"] is True

    # 3. Module E2 assertions
    e2_res = report["module_e2"]
    assert e2_res["route_count"] == 8
    assert e2_res["portfolio_fuel_saving_pct"] <= MAX_PLAUSIBLE_SAVING_PCT
    assert e2_res["total_fuel_saved_tons"] > 0
    assert e2_res["total_co2_reduced_kg"] > 0
    assert e2_res["total_cost_saved_usd"] > 0
    assert e2_res["challenge_10_passed"] is True

    # 4. Report artifact existence and non-emptiness
    report_file = Path(report["report_path"])
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "Headline Backtested Deliverables" in content
    assert f"{d_res['aggregate_saving_pct']:.2f}%" in content
    assert f"{e1_res['aggregate_cost_saved_pct']:.2f}%" in content
    assert f"{e2_res['total_fuel_saved_tons']:.2f}" in content
    assert "Challenge 10 Sanity Bound" in content
