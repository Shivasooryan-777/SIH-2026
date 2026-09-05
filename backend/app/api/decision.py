"""
Module D — Decision Engine API Router
=====================================
Calculates FIX NOW vs. WAIT recommendation with quantified expected value
and risk-adjusted savings, backtested against naive baseline.
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import CargoRequest, DecisionRecommendation, Port, Route
from backend.app.services.decision_engine import (
    evaluate_decision_for_request,
    run_historical_decision_backtest,
)

router = APIRouter(prefix="/decision", tags=["Module D — Decision Engine"])


class DecisionEvaluationRequest(BaseModel):
    cargo_type: str = Field("coking_coal", description="Cargo type (e.g. coking_coal, iron_ore)")
    cargo_volume_tons: int = Field(75000, description="Cargo volume in metric tons")
    origin_port_id: int = Field(..., description="Loading port ID")
    destination_port_id: int = Field(..., description="Discharge port ID")
    desired_timeframe_days: int = Field(30, description="Laycan/decision timeframe in days")
    desired_contract_pref: Optional[str] = Field("spot", description="'spot' / 'period' / 'no_preference'")
    date: Optional[str] = Field(None, description="Evaluation date (YYYY-MM-DD, defaults to today)")
    vessel_in_transit: bool = Field(False, description="Whether vessel is already in transit (triggers Module E2)")
    distance_remaining_nm: Optional[float] = Field(None, description="Remaining sailing distance in nm (if in transit)")


@router.get("/")
def get_decision_status():
    """Returns Module D Decision Engine status."""
    return {
        "module": "D — Decision Engine",
        "status": "active",
        "description": "Quantified expected-value FIX NOW vs WAIT recommendation with risk premium adjustment",
    }


@router.post("/evaluate")
def evaluate_decision(
    req: DecisionEvaluationRequest,
    db: Session = Depends(get_db),
):
    """
    Execute full end-to-end decision workflow:
    1. Module B: Compatible vessel ranking (largest-safe-first).
    2. Module C: Route risk radar check.
    3. Module D: Expected-value calculation and DecisionRecommendations persistence.
    4. Module E: Spot vs. Period Structuring and Speed/Fuel Advisory (if in transit).
    """
    # Verify origin and destination ports
    origin = db.query(Port).filter(Port.port_id == req.origin_port_id).first()
    dest = db.query(Port).filter(Port.port_id == req.destination_port_id).first()
    if not origin or not dest:
        raise HTTPException(status_code=404, detail="Origin or destination port not found")

    # Create CargoRequest record
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

    # Evaluate decision
    try:
        decision_result = evaluate_decision_for_request(
            request=cargo_req,
            db=db,
            eval_date=eval_dt.date(),
        )

        # Surface Module E output per blueprint Section 5 Steps 7-8
        try:
            from backend.app.services.idle_contract import evaluate_idle_contract_for_request
            idle_result = evaluate_idle_contract_for_request(
                request=cargo_req,
                db=db,
                eval_date=eval_dt.date(),
                vessel_in_transit=req.vessel_in_transit,
                distance_remaining_nm=req.distance_remaining_nm,
                persist_records=True,
            )
            decision_result["idle_contract"] = idle_result
        except Exception as idle_exc:
            decision_result["idle_contract_error"] = str(idle_exc)

        return decision_result
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Decision evaluation failed: {exc}")



@router.get("/backtest-report")
def get_backtest_report(db: Session = Depends(get_db)):
    """
    Run 25-fixture historical backtest against naive baseline and return results.
    Enforces Challenge 10 sanity check (< 25% savings).
    """
    try:
        report = run_historical_decision_backtest(db=db)
        return report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Backtest execution failed: {exc}")
