"""
Module D — Decision Engine
==========================
Implements the quantified expected-value FIX NOW vs. WAIT chartering decision
per docs/blueprint.md Module D:

1. Exact Mathematical Formula:
   F_now      = ForecastResults.p50_price for target_date = today
   F_wait(N)  = ForecastResults.p50_price for target_date = today + N days
   spread(N)  = ForecastResults.p90_price - ForecastResults.p10_price at day N
   risk_mult  = 1.50 if RiskFlags.risk_level == 'high' else
                1.15 if RiskFlags.risk_level == 'elevated' else 1.00

   RiskPremium(N) = 0.5 * spread(N) * risk_mult
   ExpectedValueOfWaiting(N) = (F_now - F_wait(N)) - RiskPremium(N)

   DECISION RULE:
     IF ExpectedValueOfWaiting(N) > 0 -> Recommend WAIT (window N*, saving = EVW(N*))
     ELSE                             -> Recommend FIX NOW (cost avoided vs waiting)

2. Historical 25-Fixture Backtest Harness:
   Evaluates 25 representative fixtures across real seeded shipping routes against
   a naive 'always fix immediately' baseline under strict temporal non-leakage.

3. Challenge 10 Sanity Guardrail:
   Loudly flags and halts if aggregate backtest savings exceed 20–25% (indicative of
   unrealistic free-arbitrage or lookahead leakage).
"""

import logging
from datetime import date as DateType, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from backend.app.models import (
    CargoRequest,
    DecisionRecommendation,
    ForecastResult,
    Port,
    RiskFlag,
    Route,
    VesselType,
)
from backend.app.services.port_matching import evaluate_port_compatibility
from backend.app.services.risk_radar import evaluate_market_risk, load_freight_series_for_volatility

logger = logging.getLogger("backend.services.decision_engine")

REPO_ROOT = Path(__file__).resolve().parents[3]

# Challenge 10 Maximum Allowable Backtest Saving Threshold
MAX_PLAUSIBLE_SAVING_PCT = 25.0

# Production candidate wait horizons (N days)
# Scoped strictly to [7, 14] following Session 6 diagnostic finding:
# Recursive multi-step forecasting systematically dampens P50 predictions further
# at longer horizons (21/28 days), mechanically biasing the engine toward defaulting
# to N=28 (77.8% of historical WAIT recommendations). Live candidate windows are restricted
# to [7, 14] where the model behaves with validated empirical reliability.
CANDIDATE_HORIZONS: List[int] = [7, 14]



def calculate_expected_value_of_waiting(
    f_now: float,
    f_wait_n: float,
    spread_n: float,
    risk_level: str,
) -> Tuple[float, float, float]:
    """
    Exact implementation of docs/blueprint.md Module D expected-value formula:
    risk_mult = 1.5 if high, 1.15 if elevated, 1.0 if calm
    RiskPremium(N) = 0.5 * spread(N) * risk_mult
    ExpectedValueOfWaiting(N) = (F_now - F_wait(N)) - RiskPremium(N)

    Returns:
        Tuple[float, float, float]: (expected_value_usd, risk_premium_usd, gross_drop_usd)
    """
    if risk_level == "high":
        risk_mult = 1.50
    elif risk_level == "elevated":
        risk_mult = 1.15
    else:
        risk_mult = 1.00

    risk_premium = 0.5 * spread_n * risk_mult
    gross_drop = f_now - f_wait_n
    evw = gross_drop - risk_premium

    return round(evw, 2), round(risk_premium, 2), round(gross_drop, 2)


def make_chartering_decision(
    f_now: float,
    horizon_forecasts: List[Dict],  # Each with: horizon_days, p50_price, spread
    risk_level: str,
    candidate_horizons: Optional[List[int]] = None,
) -> Dict:
    """
    Apply the Decision Rule across candidate wait horizons (restricted to N in {7, 14} days).
    Finds optimal window N* maximizing ExpectedValueOfWaiting(N).
    Filters input forecasts to evaluate only horizons present in candidate_horizons.
    """
    allowed_horizons = candidate_horizons if candidate_horizons is not None else CANDIDATE_HORIZONS
    valid_forecasts = [h for h in horizon_forecasts if h.get("horizon_days") in allowed_horizons]
    if not valid_forecasts:
        # Fallback to provided forecasts if none matched allowed_horizons
        valid_forecasts = horizon_forecasts

    evaluations = []
    for h in valid_forecasts:
        n_days = h["horizon_days"]
        f_wait = h["p50_price"]
        spread = h["spread"]

        evw, premium, gross = calculate_expected_value_of_waiting(
            f_now=f_now,
            f_wait_n=f_wait,
            spread_n=spread,
            risk_level=risk_level,
        )

        evaluations.append({
            "horizon_days": n_days,
            "target_date": h.get("target_date"),
            "f_wait": f_wait,
            "spread": spread,
            "gross_price_change": gross,
            "risk_premium": premium,
            "expected_value_of_waiting": evw,
        })

    # Pick N* maximizing EVW
    best_option = max(evaluations, key=lambda x: x["expected_value_of_waiting"])

    if best_option["expected_value_of_waiting"] > 0:
        action = "wait"
        expected_savings = best_option["expected_value_of_waiting"]
        recommended_window = best_option["horizon_days"]
        expected_price = best_option["f_wait"]
        reason = (
            f"Recommend WAIT ({recommended_window}-day window): Forecasted freight drop of "
            f"${best_option['gross_price_change']:.2f}/day exceeds the risk-adjusted caution penalty "
            f"of ${best_option['risk_premium']:.2f}/day (net expected saving: ${expected_savings:.2f}/day)."
        )
    else:
        action = "fix_now"
        # Cost avoided versus waiting for the worse alternative
        expected_savings = abs(best_option["expected_value_of_waiting"])
        recommended_window = 0
        expected_price = f_now
        reason = (
            f"Recommend FIX NOW: Expected value of waiting is negative across all forward horizons "
            f"(best EVW: ${best_option['expected_value_of_waiting']:.2f}/day). Chartering now avoids "
            f"adverse market volatility exposure of ${best_option['risk_premium']:.2f}/day."
        )

    return {
        "recommended_action": action,  # 'fix_now' or 'wait'
        "recommended_window_days": recommended_window,  # 0 if fix_now, N* if wait
        "expected_price": round(expected_price, 2),
        "expected_savings_usd": round(expected_savings, 2),
        "f_now": round(f_now, 2),
        "risk_level": risk_level,
        "reason": reason,
        "horizon_evaluations": evaluations,
    }


def evaluate_decision_for_request(
    request: CargoRequest,
    db: Session,
    eval_date: Optional[DateType] = None,
) -> Dict:
    """
    End-to-end recommendation workflow (Section 5):
    1. Module B: evaluate destination port compatibility and rank vessels largest-safe-first.
    2. Module C: evaluate route risk radar flags.
    3. Module D: calculate ExpectedValueOfWaiting(N) and generate DecisionRecommendations record.
    """
    req_date = eval_date or (request.created_at.date() if request.created_at else datetime.now(timezone.utc).date())

    dest_port = db.query(Port).filter(Port.port_id == request.destination_port_id).first()
    if not dest_port:
        raise ValueError(f"Destination port ID {request.destination_port_id} not found")

    # Step 1: Module B Port Compatibility
    cargo_vol_raw = getattr(request, "cargo_volume_tons", None)
    cargo_vol_int: Optional[int] = int(cargo_vol_raw) if cargo_vol_raw is not None else None
    port_matching = evaluate_port_compatibility(
        port=dest_port,
        eval_date=req_date,
        db=db,
        cargo_volume_tons=cargo_vol_int,
    )

    if not port_matching["ranked_compatible_vessels"]:
        raise ValueError(f"No compatible vessel types found for port {dest_port.name} on {req_date}")

    top_vessel_info = port_matching["ranked_compatible_vessels"][0]
    recommended_vessel_id = top_vessel_info["vessel_type_id"]

    # Step 2: Module C Risk Radar
    # Find route between origin and destination
    route_obj = db.query(Route).filter(
        Route.origin_port_id == request.origin_port_id,
        Route.destination_port_id == request.destination_port_id,
    ).first()
    route_id_raw = getattr(route_obj, "route_id", None) if route_obj else None
    route_id: Optional[int] = int(route_id_raw) if route_id_raw is not None else None

    risk_result = evaluate_market_risk(eval_date=req_date, route_id=route_id, db=db, persist_flag=True)
    risk_level = risk_result["risk_level"]

    # Step 3: Module A Forecast Lookup
    # Live runtime: query ForecastResults from DB (vessel_type_id=NULL, general series)
    recent_forecasts = (
        db.query(ForecastResult)
        .filter(ForecastResult.vessel_type_id.is_(None))
        .order_by(ForecastResult.generated_at.desc())
        .limit(30)
        .all()
    )

    if recent_forecasts:
        f_now = float(recent_forecasts[0].p50_price)
        candidate_horizons = CANDIDATE_HORIZONS
        horizon_forecasts = []
        for h in candidate_horizons:
            idx = min(h, len(recent_forecasts) - 1)
            fc = recent_forecasts[idx]
            p10 = float(fc.p10_price)
            p50 = float(fc.p50_price)
            p90 = float(fc.p90_price)
            horizon_forecasts.append({
                "horizon_days": h,
                "target_date": (req_date + timedelta(days=h)).isoformat(),
                "p50_price": p50,
                "spread": round(p90 - p10, 2),
            })
    else:
        # Fall back to local out-of-fold forecast table if live table empty
        csv_path = REPO_ROOT / "data" / "processed" / "oof_forecasts_series.csv"
        if not csv_path.exists():
            raise FileNotFoundError("No live forecasts in DB and missing oof_forecasts_series.csv!")
        oof_df = pd.read_csv(csv_path)
        avail_dates = oof_df["origin_date"].unique()
        closest_date = min(avail_dates, key=lambda d: abs((datetime.strptime(d, "%Y-%m-%d").date() - req_date).days))
        subset = oof_df[oof_df["origin_date"] == closest_date]
        subset = subset[subset["horizon_days"].isin(CANDIDATE_HORIZONS)]
        f_now = float(subset["f_now"].iloc[0])
        horizon_forecasts = [
            {
                "horizon_days": int(r["horizon_days"]),
                "target_date": str(r["target_date"]),
                "p50_price": float(r["p50_price"]),
                "spread": float(r["spread"]),
            }
            for _, r in subset.iterrows()
        ]

    # Step 4: Decision Computation
    decision = make_chartering_decision(
        f_now=f_now,
        horizon_forecasts=horizon_forecasts,
        risk_level=risk_level,
        candidate_horizons=CANDIDATE_HORIZONS,
    )

    # Step 5: Persist DecisionRecommendations record (Option 3B: locked 7-column schema)
    rec_record = DecisionRecommendation(
        request_id=request.request_id,
        recommended_vessel_type_id=recommended_vessel_id,
        recommended_action=decision["recommended_action"],
        expected_price=Decimal(str(decision["expected_price"])),
        expected_savings_usd=Decimal(str(decision["expected_savings_usd"])),
    )
    db.add(rec_record)
    db.commit()
    db.refresh(rec_record)

    return {
        "decision_id": rec_record.decision_id,
        "request_id": request.request_id,
        "recommended_vessel_type_id": recommended_vessel_id,
        "recommended_vessel_name": top_vessel_info["name"],
        "recommended_action": decision["recommended_action"],
        "recommended_window_days": decision["recommended_window_days"],
        "expected_price": decision["expected_price"],
        "expected_savings_usd": decision["expected_savings_usd"],
        "risk_level": risk_level,
        "risk_multiplier": risk_result["risk_multiplier"],
        "reason": decision["reason"],
        "generated_at": rec_record.generated_at.isoformat() if rec_record.generated_at else datetime.now(timezone.utc).isoformat(),
        "port_compatibility": port_matching,
        "horizon_evaluations": decision["horizon_evaluations"],
    }


# =============================================================================
# 25-Fixture Backtest Simulation Against Naive Baseline
# =============================================================================

# 25 Realistic historical fixtures drawn strictly from the 8 seeded routes
HISTORICAL_FIXTURE_SPECS = [
    # (origin_date, route_id, cargo_type, cargo_volume_tons, timeframe_days)
    ("2020-04-15", 1, "coking_coal", 35000, 30),  # Taboneo -> Haldia
    ("2020-06-16", 2, "coking_coal", 55000, 30),  # Taboneo -> Paradip_Inner
    ("2020-08-18", 3, "coking_coal", 85000, 30),  # Maputo -> Dhamra
    ("2020-10-20", 4, "coking_coal", 50000, 30),  # Beira -> Dhamra
    ("2020-12-15", 5, "coking_coal", 150000, 30), # Nacala -> Gangavaram
    ("2021-02-16", 6, "coking_coal", 80000, 30),  # Vostochny_PPK3 -> Vizag_Outer
    ("2021-04-20", 7, "coking_coal", 170000, 30), # Newcastle -> Paradip_SPM
    ("2021-06-15", 8, "coking_coal", 75000, 30),  # Lamberts_Point -> Vizag_Outer
    ("2021-08-17", 1, "coking_coal", 30000, 30),  # Taboneo -> Haldia
    ("2021-10-19", 2, "coking_coal", 60000, 30),  # Taboneo -> Paradip_Inner
    ("2021-12-14", 3, "coking_coal", 90000, 30),  # Maputo -> Dhamra
    ("2022-02-15", 4, "coking_coal", 45000, 30),  # Beira -> Dhamra
    ("2022-04-19", 5, "coking_coal", 160000, 30), # Nacala -> Gangavaram
    ("2022-06-21", 6, "coking_coal", 85000, 30),  # Vostochny_PPK3 -> Vizag_Outer
    ("2022-08-16", 7, "coking_coal", 175000, 30), # Newcastle -> Paradip_SPM
    ("2022-10-18", 8, "coking_coal", 75000, 30),  # Lamberts_Point -> Vizag_Outer
    ("2022-12-20", 1, "coking_coal", 35000, 30),  # Taboneo -> Haldia
    ("2023-02-21", 2, "coking_coal", 60000, 30),  # Taboneo -> Paradip_Inner
    ("2023-04-18", 3, "coking_coal", 85000, 30),  # Maputo -> Dhamra
    ("2023-06-20", 4, "coking_coal", 50000, 30),  # Beira -> Dhamra
    ("2023-08-15", 5, "coking_coal", 150000, 30), # Nacala -> Gangavaram
    ("2023-10-17", 6, "coking_coal", 80000, 30),  # Vostochny_PPK3 -> Vizag_Outer
    ("2023-12-19", 7, "coking_coal", 165000, 30), # Newcastle -> Paradip_SPM
    ("2024-02-20", 8, "coking_coal", 75000, 30),  # Lamberts_Point -> Vizag_Outer
    ("2024-04-16", 2, "coking_coal", 55000, 30),  # Taboneo -> Paradip_Inner
]


def run_historical_decision_backtest(
    db: Session,
    oof_csv_path: Optional[Path] = None,
) -> Dict:
    """
    Execute 25-fixture historical backtest against naive baseline.
    Computes real realized chartering costs and net savings percentage.
    Enforces Challenge 10 sanity check (< 25% savings).
    """
    csv_file = oof_csv_path or (REPO_ROOT / "data" / "processed" / "oof_forecasts_series.csv")
    if not csv_file.exists():
        raise FileNotFoundError(f"Missing out-of-fold forecasts: {csv_file}. Run ml/export_oof_forecasts.py first!")

    oof_df = pd.read_csv(csv_file)
    freight_df = load_freight_series_for_volatility(db=db)
    freight_df["date_str"] = freight_df["date"].dt.strftime("%Y-%m-%d")
    date_to_actual_price = dict(zip(freight_df["date_str"], freight_df["price"]))

    results: List[Dict] = []
    total_baseline_cost = 0.0
    total_engine_cost = 0.0

    for idx, (origin_date, route_id, cargo_type, volume, timeframe) in enumerate(HISTORICAL_FIXTURE_SPECS, start=1):
        t0_date = datetime.strptime(origin_date, "%Y-%m-%d").date()

        route = db.query(Route).filter(Route.route_id == route_id).first()
        if not route:
            raise ValueError(f"Route ID {route_id} not found in database!")

        dest_port = db.query(Port).filter(Port.port_id == route.destination_port_id).first()
        origin_port = db.query(Port).filter(Port.port_id == route.origin_port_id).first()

        # 1. Module B compatibility
        port_res = evaluate_port_compatibility(dest_port, t0_date, db, cargo_volume_tons=volume)
        compatible_vessels = port_res["ranked_compatible_vessels"]
        top_vessel = compatible_vessels[0]["name"] if compatible_vessels else "None"

        # 2. Module C risk check
        risk_res = evaluate_market_risk(t0_date, route_id=route_id, db=db, persist_flag=False, freight_df=freight_df)
        risk_level = risk_res["risk_level"]

        # 3. Module D decision computation
        subset = oof_df[oof_df["origin_date"] == origin_date]
        if subset.empty:
            raise ValueError(f"No out-of-fold forecasts for origin {origin_date}")

        subset = subset[subset["horizon_days"].isin(CANDIDATE_HORIZONS)]
        f_now = float(subset["f_now"].iloc[0])
        horizon_forecasts = [
            {
                "horizon_days": int(r["horizon_days"]),
                "target_date": str(r["target_date"]),
                "p50_price": float(r["p50_price"]),
                "spread": float(r["spread"]),
            }
            for _, r in subset.iterrows()
        ]

        decision = make_chartering_decision(
            f_now=f_now,
            horizon_forecasts=horizon_forecasts,
            risk_level=risk_level,
            candidate_horizons=CANDIDATE_HORIZONS,
        )
        action = decision["recommended_action"]
        opt_window = decision["recommended_window_days"]

        # 4. Realized price evaluation
        # Actual price at t0
        actual_p_t0 = date_to_actual_price.get(origin_date)
        if actual_p_t0 is None:
            # Snap to closest prior trading date
            prior_dates = [d for d in date_to_actual_price if d <= origin_date]
            actual_p_t0 = date_to_actual_price[max(prior_dates)]

        # Baseline policy: fixes immediately at t0
        baseline_price = actual_p_t0

        # Decision Engine policy:
        if action == "wait" and opt_window > 0:
            target_date_str = str(datetime.strptime(origin_date, "%Y-%m-%d") + timedelta(days=opt_window))[:10]
            # Realized actual spot rate on fixing date
            if target_date_str in date_to_actual_price:
                engine_price = date_to_actual_price[target_date_str]
            else:
                prior_dates = [d for d in date_to_actual_price if d <= target_date_str]
                engine_price = date_to_actual_price[max(prior_dates)]
        else:
            engine_price = actual_p_t0

        realized_saving_usd = baseline_price - engine_price
        realized_saving_pct = (realized_saving_usd / baseline_price) * 100.0

        total_baseline_cost += baseline_price
        total_engine_cost += engine_price

        results.append({
            "fixture_id": idx,
            "origin_date": origin_date,
            "route": f"{origin_port.name} -> {dest_port.name}",
            "cargo_volume": volume,
            "recommended_vessel": top_vessel,
            "risk_level": risk_level,
            "action": action,
            "window_days": opt_window,
            "baseline_spot_usd": round(baseline_price, 2),
            "engine_spot_usd": round(engine_price, 2),
            "realized_saving_usd": round(realized_saving_usd, 2),
            "realized_saving_pct": round(realized_saving_pct, 2),
        })

    # Compute aggregate portfolio savings
    aggregate_saving_usd = total_baseline_cost - total_engine_cost
    aggregate_saving_pct = (aggregate_saving_usd / total_baseline_cost) * 100.0

    logger.info("=== 25-FIXTURE HISTORICAL BACKTEST SUMMARY ===")
    logger.info("Total Baseline Portfolio Cost: $%.2f", total_baseline_cost)
    logger.info("Total Decision Engine Cost:    $%.2f", total_engine_cost)
    logger.info("Total Net Dollar Savings:      $%.2f", aggregate_saving_usd)
    logger.info("Aggregate Portfolio Saving:    %.2f %%", aggregate_saving_pct)

    # CRITICAL SANITY CHECK (docs/blueprint.md Challenge 10)
    if aggregate_saving_pct > MAX_PLAUSIBLE_SAVING_PCT:
        raise ValueError(
            f"CHALLENGE 10 VIOLATION: Aggregate backtest saving of {aggregate_saving_pct:.2f}% "
            f"exceeds the 25.0% plausible threshold! HALT: Treat as lookahead leakage signal."
        )

    return {
        "fixture_count": len(results),
        "total_baseline_cost_usd": round(total_baseline_cost, 2),
        "total_engine_cost_usd": round(total_engine_cost, 2),
        "aggregate_saving_usd": round(aggregate_saving_usd, 2),
        "aggregate_saving_pct": round(aggregate_saving_pct, 2),
        "fixtures": results,
    }
