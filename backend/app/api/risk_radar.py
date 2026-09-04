"""
Module C — Risk Radar API Router
=================================
Exposes endpoints for:
1. Always-On Market Watch status and persistent sentiment overview.
2. Query-driven route risk evaluation (calm/elevated/high).
3. Historical event replay backtest verification report.
"""

from datetime import date as DateType, datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import RiskFlag, Route
from backend.app.services.risk_radar import (
    evaluate_market_risk,
    replay_historical_risk_events,
)

router = APIRouter(prefix="/risk-radar", tags=["Module C — Risk Radar"])


@router.get("/")
def get_risk_radar_status(db: Session = Depends(get_db)):
    """
    Returns Module C status and current Always-On Market Watch sentiment.
    """
    today = datetime.now(timezone.utc).date()
    current_eval = evaluate_market_risk(eval_date=today, db=db, persist_flag=False)

    return {
        "module": "C — Risk Radar",
        "status": "active",
        "market_sentiment": current_eval["risk_level"],
        "reason": current_eval["reason"],
        "current_metrics": current_eval["metrics"],
        "as_of_date": today.isoformat(),
    }


@router.get("/active")
def get_active_risk_flags(db: Session = Depends(get_db)):
    """
    Returns all currently active RiskFlags persisted in the database.
    """
    active_flags = (
        db.query(RiskFlag)
        .filter(RiskFlag.is_active == True)
        .order_by(RiskFlag.date.desc())
        .limit(20)
        .all()
    )

    return {
        "count": len(active_flags),
        "flags": [
            {
                "flag_id": f.flag_id,
                "date": f.date.isoformat(),
                "route_id": f.route_id,
                "risk_level": f.risk_level,
                "reason": f.reason,
                "is_active": f.is_active,
            }
            for f in active_flags
        ],
    }


@router.get("/evaluate")
def evaluate_risk(
    route_id: Optional[int] = Query(None, description="Optional route ID to check route-specific risk"),
    date_str: Optional[str] = Query(None, alias="date", description="Date YYYY-MM-DD (defaults to today)"),
    db: Session = Depends(get_db),
):
    """
    Evaluate quantitative risk level and active disruptions for a given date and route.
    """
    eval_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.now(timezone.utc).date()

    if route_id is not None:
        route_obj = db.query(Route).filter(Route.route_id == route_id).first()
        if not route_obj:
            raise HTTPException(status_code=404, detail=f"Route #{route_id} not found")

    return evaluate_market_risk(
        eval_date=eval_date,
        route_id=route_id,
        db=db,
        persist_flag=True,
    )


@router.get("/backtest-report")
def get_historical_backtest_report(db: Session = Depends(get_db)):
    """
    Replay the 4 curated RiskEvents and return the full verification report.
    """
    df = replay_historical_risk_events(db=db)
    return {
        "event_count": len(df),
        "caught_count": int((df["caught"] == "YES").sum()),
        "catch_rate_pct": round(float((df["caught"] == "YES").mean() * 100.0), 1),
        "events": df.to_dict(orient="records"),
    }
