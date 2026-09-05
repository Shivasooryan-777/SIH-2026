"""
Module E — Idle-Time & Contract Structuring API Router
======================================================
Provides endpoints for:
1. Module E1: Spot-vs-period structuring recommendation (trough detection, 14-day horizon).
2. Module E2: Just-In-Time (JIT) speed & fuel optimization advisory for vessels in transit.
3. Historical backtest reports for E1, E2, and unified 3-module report.
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import CargoRequest, Port, Route
from backend.app.services.idle_contract import (
    DEFAULT_BUNKER_FUEL_PRICE_USD_PER_TON,
    DEFAULT_PORT_CONGESTION_HOURS,
    DEFAULT_SAFETY_BUFFER_HOURS,
    DEFAULT_TROUGH_WINDOW_DAYS,
    evaluate_idle_contract_for_request,
)
from ml.backtest import (
    generate_unified_backtest_report,
    run_idle_time_backtest,
    run_speed_backtest,
)

router = APIRouter(prefix="/idle-contract", tags=["Module E — Idle-Time & Contract Structuring"])


class IdleContractEvaluationRequest(BaseModel):
    cargo_type: str = Field("coking_coal", description="Cargo type (e.g. coking_coal, iron_ore)")
    cargo_volume_tons: int = Field(75000, description="Cargo volume in metric tons")
    origin_port_id: int = Field(..., description="Loading port ID")
    destination_port_id: int = Field(..., description="Discharge port ID")
    desired_timeframe_days: int = Field(30, description="Laycan/decision timeframe in days")
    desired_contract_pref: Optional[str] = Field("no_preference", description="'spot' / 'period' / 'no_preference'")
    date: Optional[str] = Field(None, description="Evaluation date (YYYY-MM-DD, defaults to today)")
    trough_window_days: int = Field(
        DEFAULT_TROUGH_WINDOW_DAYS,
        description="Contiguous low-price window required to declare a trough (default: 14 days)",
    )
    vessel_in_transit: bool = Field(
        False,
        description="True if vessel has sailed and is currently in transit (conditional trigger for Module E2)",
    )
    distance_remaining_nm: Optional[float] = Field(
        None,
        description="Remaining sailing distance in nautical miles (for in-transit vessels)",
    )
    expected_port_congestion_hours: Optional[float] = Field(
        DEFAULT_PORT_CONGESTION_HOURS,
        description="Forecasted waiting time at destination port in hours (default: 36.0h)",
    )
    safety_buffer_hours: float = Field(
        DEFAULT_SAFETY_BUFFER_HOURS,
        description="Operational buffer before absorbing port delay (default: 4.0h)",
    )
    bunker_price_usd_per_ton: float = Field(
        DEFAULT_BUNKER_FUEL_PRICE_USD_PER_TON,
        description="Bunker fuel price benchmark in USD per metric ton (default: $600/t VLSFO)",
    )


@router.get("/")
def get_idle_contract_status():
    """Returns Module E Idle-Time & Contract Structuring status."""
    return {
        "module": "E — Idle-Time & Contract Structuring",
        "status": "active",
        "description": "E1 Spot-vs-period structuring recommendation and E2 Speed & fuel optimization advisory (JIT)",
        "default_trough_window_days": DEFAULT_TROUGH_WINDOW_DAYS,
        "default_bunker_fuel_price_usd_per_ton": DEFAULT_BUNKER_FUEL_PRICE_USD_PER_TON,
        "default_port_congestion_hours": DEFAULT_PORT_CONGESTION_HOURS,
    }


@router.post("/evaluate")
def evaluate_idle_contract(
    req: IdleContractEvaluationRequest,
    db: Session = Depends(get_db),
):
    """
    Evaluate Module E advisory for a cargo fixture:
    1. Module E1: Detects forward freight troughs and recommends spot vs. period chartering.
    2. Module E2: If vessel is in transit, computes JIT slow-steaming advisory and emissions savings.
    Persists IdleTimeAnalysis and (if in transit) SpeedOptimizationLog records.
    """
    origin = db.query(Port).filter(Port.port_id == req.origin_port_id).first()
    dest = db.query(Port).filter(Port.port_id == req.destination_port_id).first()
    if not origin or not dest:
        raise HTTPException(status_code=404, detail="Origin or destination port not found")

    eval_dt = datetime.strptime(req.date, "%Y-%m-%d") if req.date else datetime.now(timezone.utc)

    cargo_req = CargoRequest(
        created_at=eval_dt,
        cargo_type=req.cargo_type,
        cargo_volume_tons=req.cargo_volume_tons,
        origin_port_id=req.origin_port_id,
        destination_port_id=req.destination_port_id,
        desired_timeframe_days=req.desired_timeframe_days,
        desired_contract_pref=(
            req.desired_contract_pref[:10]
            if req.desired_contract_pref and len(req.desired_contract_pref) <= 10
            else None
        ),
    )
    db.add(cargo_req)
    db.commit()
    db.refresh(cargo_req)

    try:
        result = evaluate_idle_contract_for_request(
            request=cargo_req,
            db=db,
            eval_date=eval_dt.date(),
            trough_window_days=req.trough_window_days,
            vessel_in_transit=req.vessel_in_transit,
            distance_remaining_nm=req.distance_remaining_nm,
            expected_port_congestion_hours=req.expected_port_congestion_hours,
            safety_buffer_hours=req.safety_buffer_hours,
            bunker_price_usd_per_ton=req.bunker_price_usd_per_ton,
            persist_records=True,
        )
        return result
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Module E evaluation failed: {exc}")


@router.get("/backtest-report")
def get_idle_time_backtest_report(
    trough_window_days: int = Query(DEFAULT_TROUGH_WINDOW_DAYS, description="Trough window in days"),
    db: Session = Depends(get_db),
):
    """
    Run historical backtest for Module E1 (Spot-only vs. Period-charter-when-trough-detected).
    Reports cost delta and idle-days avoided under strict temporal non-leakage.
    """
    try:
        report = run_idle_time_backtest(db=db, trough_window_days=trough_window_days)
        return report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Module E1 backtest failed: {exc}")


@router.get("/speed-backtest-report")
def get_speed_backtest_report(
    congestion_hours: float = Query(DEFAULT_PORT_CONGESTION_HOURS, description="Port congestion hours"),
    bunker_price: float = Query(DEFAULT_BUNKER_FUEL_PRICE_USD_PER_TON, description="Bunker fuel price USD/ton"),
    db: Session = Depends(get_db),
):
    """
    Run simulation for Module E2 (Speed & Fuel Optimization Advisory) across shipping corridors.
    Reports fuel saved (tons), CO2 reduced (kg/tons), and bunker fuel cost saved ($).
    """
    try:
        report = run_speed_backtest(
            db=db,
            port_congestion_hours=congestion_hours,
            bunker_price_usd_per_ton=bunker_price,
        )
        return report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Module E2 backtest failed: {exc}")


@router.get("/unified-backtest-report")
def get_unified_backtest_report(db: Session = Depends(get_db)):
    """
    Run consolidated backtest across Modules D, E1, and E2 and return comprehensive summary.
    Enforces Challenge 10 sanity guardrail (<= 25.0% savings) across all models.
    """
    try:
        report = generate_unified_backtest_report(db=db)
        return report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unified backtest failed: {exc}")
