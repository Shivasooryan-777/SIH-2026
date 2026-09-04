"""
Module D — Decision Engine Test Suite
=====================================
Verifies:
1. Exact Expected-Value Mathematical Formula:
   EVW(N) = (F_now - F_wait(N)) - (0.5 * spread(N) * risk_mult)
   across Calm (1.0x), Elevated (1.15x), and High (1.50x) risk regimes.
2. Decision Rule behavior: WAIT when EVW > 0, FIX NOW when EVW <= 0.
3. 25-FIXTURE HISTORICAL BACKTEST:
   Executes 25 simulated cargo movements against naive baseline and computes real realized savings.
4. CHALLENGE 10 CRITICAL SANITY GUARDRAIL:
   Asserts aggregate saving <= 25%, and verifies that savings > 25% are loudly rejected
   as leakage signals rather than accepted.
5. End-to-end decision workflow and database persistence.
"""

from datetime import date
from decimal import Decimal
import pytest
import pandas as pd

from backend.app.database import SessionLocal
from backend.app.models import CargoRequest, DecisionRecommendation, Port, Route, VesselType
from backend.app.services.decision_engine import (
    calculate_expected_value_of_waiting,
    make_chartering_decision,
    evaluate_decision_for_request,
    run_historical_decision_backtest,
    MAX_PLAUSIBLE_SAVING_PCT,
)


@pytest.fixture(scope="function")
def db_session():
    """Function-scoped database session for decision engine tests with clean rollback."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_expected_value_formula_exact_computation():
    """
    Test exact expected-value arithmetic against hand-computed values:
    F_now = 25.00, F_wait = 21.00, spread = 4.00
    Gross drop = 25.00 - 21.00 = +4.00
    """
    f_now = 25.00
    f_wait = 21.00
    spread = 4.00

    # 1. Calm: risk_mult = 1.00 -> premium = 0.5 * 4.0 * 1.0 = 2.00 -> EVW = 4.00 - 2.00 = +2.00
    evw_calm, prem_calm, gross_calm = calculate_expected_value_of_waiting(f_now, f_wait, spread, "calm")
    assert gross_calm == 4.00
    assert prem_calm == 2.00
    assert evw_calm == 2.00

    # 2. Elevated: risk_mult = 1.15 -> premium = 0.5 * 4.0 * 1.15 = 2.30 -> EVW = 4.00 - 2.30 = +1.70
    evw_elev, prem_elev, _ = calculate_expected_value_of_waiting(f_now, f_wait, spread, "elevated")
    assert prem_elev == 2.30
    assert evw_elev == 1.70

    # 3. High: risk_mult = 1.50 -> premium = 0.5 * 4.0 * 1.50 = 3.00 -> EVW = 4.00 - 3.00 = +1.00
    evw_high, prem_high, _ = calculate_expected_value_of_waiting(f_now, f_wait, spread, "high")
    assert prem_high == 3.00
    assert evw_high == 1.00

    # 4. Inversion check: if forecasted drop (1.50) < risk premium (2.00) -> EVW is negative
    evw_neg, _, _ = calculate_expected_value_of_waiting(f_now=20.0, f_wait_n=18.5, spread_n=4.0, risk_level="calm")
    assert evw_neg == -0.50  # Gross 1.50 - Premium 2.00 = -0.50


def test_decision_rule_action_selection():
    """Verify make_chartering_decision selects WAIT when EVW > 0 and FIX NOW when EVW <= 0."""
    # Case A: Trough detected at day 14 (positive EVW) -> WAIT
    horizons_wait = [
        {"horizon_days": 7, "p50_price": 19.5, "spread": 2.0},  # drop=0.5, prem=1.0 -> evw = -0.5
        {"horizon_days": 14, "p50_price": 16.0, "spread": 2.5}, # drop=4.0, prem=1.25 -> evw = +2.75
        {"horizon_days": 21, "p50_price": 18.0, "spread": 3.0}, # drop=2.0, prem=1.5 -> evw = +0.5
    ]
    res_wait = make_chartering_decision(f_now=20.0, horizon_forecasts=horizons_wait, risk_level="calm")
    assert res_wait["recommended_action"] == "wait"
    assert res_wait["recommended_window_days"] == 14
    assert res_wait["expected_savings_usd"] == 2.75

    # Case B: Rising prices or wide spreads (negative EVW) -> FIX NOW
    horizons_fix = [
        {"horizon_days": 7, "p50_price": 21.0, "spread": 3.0},  # drop=-1.0, prem=1.5 -> evw = -2.5
        {"horizon_days": 14, "p50_price": 22.0, "spread": 4.0}, # drop=-2.0, prem=2.0 -> evw = -4.0
    ]
    res_fix = make_chartering_decision(f_now=20.0, horizon_forecasts=horizons_fix, risk_level="calm")
    assert res_fix["recommended_action"] == "fix_now"
    assert res_fix["recommended_window_days"] == 0
    assert res_fix["expected_savings_usd"] > 0  # Cost avoided vs waiting

    # Case C: Candidate horizon filtering verification (N in {7, 14} enforced)
    # Even if N=21 or N=28 has an artificially massive drop due to recursive dampening bias,
    # the Decision Engine must filter them out and evaluate ONLY N in {7, 14}.
    horizons_with_dampening_bias = [
        {"horizon_days": 7, "p50_price": 19.0, "spread": 2.0},   # drop=1.0, prem=1.0 -> evw = 0.0
        {"horizon_days": 14, "p50_price": 18.0, "spread": 2.0},  # drop=2.0, prem=1.0 -> evw = +1.0
        {"horizon_days": 21, "p50_price": 14.0, "spread": 2.0},  # drop=6.0, prem=1.0 -> evw = +5.0 (dampening artifact)
        {"horizon_days": 28, "p50_price": 10.0, "spread": 2.0},  # drop=10.0, prem=1.0 -> evw = +9.0 (dampening artifact)
    ]
    res_filtered = make_chartering_decision(f_now=20.0, horizon_forecasts=horizons_with_dampening_bias, risk_level="calm")
    # Verify candidate filtering: evaluated horizons must strictly be {7, 14}
    evaluated_horizons = [eval_item["horizon_days"] for eval_item in res_filtered["horizon_evaluations"]]
    assert evaluated_horizons == [7, 14], f"Expected only [7, 14] evaluated, got {evaluated_horizons}"
    assert res_filtered["recommended_action"] == "wait"
    assert res_filtered["recommended_window_days"] == 14  # Day 14 chosen, day 21 and 28 filtered out
    assert res_filtered["expected_savings_usd"] == 1.00   # Net saving from day 14, not 9.00 from day 28


def test_run_historical_decision_backtest_and_sanity_check(db_session):
    """
    CRITICAL DELIVERABLE:
    Runs the 25-fixture historical backtest against naive baseline.
    Verifies:
    1. Evaluates all 25 fixtures.
    2. Any WAIT recommendation strictly chooses N in {7, 14} (verifying candidate scoping).
    3. Aggregate savings DO NOT EXCEED 25.0% (Challenge 10 sanity guardrail).
    """
    report = run_historical_decision_backtest(db=db_session)

    assert report["fixture_count"] == 25, f"Expected 25 fixtures, got {report['fixture_count']}"
    assert report["total_baseline_cost_usd"] > 0
    assert report["total_engine_cost_usd"] > 0

    # Verify that all WAIT decisions chose from the restricted candidate set {7, 14}
    for f in report["fixtures"]:
        if f["action"] == "wait":
            assert f["window_days"] in (7, 14), (
                f"Fixture {f['fixture_id']} recommended window {f['window_days']} days, "
                "which is outside the restricted candidate set {7, 14}!"
            )

    agg_saving_pct = report["aggregate_saving_pct"]

    # Print the concrete backtest table for audit trail
    print("\n" + "=" * 90)
    print("MODULE D — 25-FIXTURE HISTORICAL BACKTEST RESULTS")
    print("=" * 90)
    fixtures_df = pd.DataFrame(report["fixtures"])
    summary_cols = [
        "fixture_id", "origin_date", "route", "recommended_vessel",
        "risk_level", "action", "window_days", "baseline_spot_usd",
        "engine_spot_usd", "realized_saving_pct"
    ]
    print(fixtures_df[summary_cols].to_string(index=False))
    print("-" * 90)
    print(f"Total Baseline Portfolio Cost: ${report['total_baseline_cost_usd']:.2f}")
    print(f"Total Decision Engine Cost:    ${report['total_engine_cost_usd']:.2f}")
    print(f"Total Net Savings:             ${report['aggregate_saving_usd']:.2f}")
    print(f"AGGREGATE SAVINGS:             {agg_saving_pct:.2f}% (Challenge 10 Bound: <= 25.0%)")
    print("=" * 90 + "\n")

    # Challenge 10 Sanity Assertion (saving must NOT exceed 25%)
    assert agg_saving_pct <= MAX_PLAUSIBLE_SAVING_PCT, (
        f"CHALLENGE 10 SANITY VIOLATION: Backtest savings ({agg_saving_pct}%) exceed 25%! "
        "Must be investigated as potential data leakage or lookahead bug."
    )


def test_end_to_end_decision_workflow_persistence(db_session):
    """
    Verify full workflow:
    CargoRequest -> Port-Matching -> Risk Radar -> Decision -> DecisionRecommendations persistence.
    """
    origin = db_session.query(Port).filter(Port.name == "Newcastle").first()
    dest = db_session.query(Port).filter(Port.name == "Paradip_SPM").first()
    assert origin is not None and dest is not None

    req = CargoRequest(
        cargo_type="coking_coal",
        cargo_volume_tons=160000,
        origin_port_id=origin.port_id,
        destination_port_id=dest.port_id,
        desired_timeframe_days=30,
        desired_contract_pref="spot",
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)

    result = evaluate_decision_for_request(request=req, db=db_session, eval_date=date(2023, 6, 15))

    assert result["decision_id"] is not None
    assert result["recommended_action"] in ("fix_now", "wait")
    assert result["expected_price"] > 0
    assert result["recommended_vessel_name"] in ("Capesize", "Panamax", "Supramax", "Handysize")
    assert "recommended_window_days" in result  # Option 3B returned in API response

    # Verify locked 7-column schema persistence in Neon
    persisted = db_session.query(DecisionRecommendation).filter(
        DecisionRecommendation.decision_id == result["decision_id"]
    ).first()
    assert persisted is not None
    assert persisted.recommended_action == result["recommended_action"]
    assert float(persisted.expected_price) == result["expected_price"]
