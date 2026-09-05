"""
Module F — Interaction Layer API Router
========================================
Implements the interaction architecture defined in docs/blueprint.md Section 3 & 5:
1. Layer 1: Always-On Market Watch (GET /api/interaction/market-watch)
   - Zero-parameter proactive market status endpoint.
   - Computes overall market sentiment from all active RiskFlags across all 8 corridors.
   - Returns corridor-attributed active disruption flags and leading macro metrics.
   - Designed for instant dashboard display before user submits any CargoRequest.

2. Layer 2: Mark as Actioned Decision Logging (POST /api/interaction/action)
   - Validates decision_id exists in DecisionRecommendations.
   - Writes an anonymous, timestamped ActionedDecision record (no user auth).
   - Closes the recommendation feedback loop.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import (
    ActionedDecision,
    DecisionRecommendation,
    Port,
    RiskFlag,
    Route,
)
from backend.app.services.risk_radar import evaluate_market_risk

router = APIRouter(prefix="/interaction", tags=["Module F — Interaction Layer"])


# =============================================================================
# Pydantic Schemas
# =============================================================================

class ActionDecisionRequest(BaseModel):
    decision_id: int = Field(..., description="ID of the DecisionRecommendation acted upon")
    note: Optional[str] = Field(None, description="Optional operational note or execution rationale")


class ActionDecisionResponse(BaseModel):
    status: str
    action_id: int
    decision_id: int
    actioned_at: str
    note: Optional[str] = None


class ActiveRiskFlagSummary(BaseModel):
    flag_id: int
    date: str
    route_id: Optional[int] = None
    corridor: str
    risk_level: str
    reason: str
    is_active: bool


class MarketWatchResponse(BaseModel):
    as_of_date: str
    overall_sentiment: str  # 'calm' | 'elevated' | 'high'
    summary_reason: str
    active_flags_count: int
    active_flags: List[ActiveRiskFlagSummary]
    macro_metrics: Dict[str, Any]


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/", summary="Module F Interaction Layer Status")
def get_interaction_status():
    """Status endpoint for Module F Interaction Layer."""
    return {
        "module": "F — Interaction Layer",
        "status": "active",
        "description": "Always-On Market Watch, query-driven recommendations, and anonymous action logging",
        "endpoints": [
            "GET /api/interaction/market-watch",
            "POST /api/interaction/action",
        ],
    }


@router.get(
    "/market-watch",
    response_model=MarketWatchResponse,
    summary="Layer 1: Always-On Market Watch Status",
)
def get_always_on_market_watch(db: Session = Depends(get_db)):
    """
    Module F Layer 1 — Always-On Market Watch.
    Callable with zero parameters on initial dashboard load.
    - Scans active RiskFlags across all 8 corridors.
    - Derives overall market sentiment hierarchically (high > elevated > calm).
    - Returns plain-language summary and corridor-attributed flags.
    """
    today = datetime.now(timezone.utc).date()

    # 1. Fetch all currently active RiskFlags
    active_flags_query = (
        db.query(RiskFlag)
        .filter(RiskFlag.is_active == True)
        .order_by(RiskFlag.date.desc())
        .all()
    )

    # 2. Build lookup maps for corridor names (Origin -> Destination)
    routes = {r.route_id: r for r in db.query(Route).all()}
    ports = {p.port_id: p.name for p in db.query(Port).all()}

    flag_summaries: List[ActiveRiskFlagSummary] = []
    has_high = False
    has_elevated = False

    for f in active_flags_query:
        lvl = (f.risk_level or "calm").lower()
        if lvl == "high":
            has_high = True
        elif lvl == "elevated":
            has_elevated = True

        r = routes.get(f.route_id) if f.route_id else None
        if r:
            orig_name = ports.get(r.origin_port_id, "Origin")
            dest_name = ports.get(r.destination_port_id, "Destination")
            corridor_str = f"{orig_name} -> {dest_name}"
        else:
            corridor_str = "Global Macro / Unassigned"

        flag_dt = getattr(f, "date", None)
        flag_date_str = (
            flag_dt.isoformat()
            if hasattr(flag_dt, "isoformat")
            else str(flag_dt or "")
        )
        flag_route_id = getattr(f, "route_id", None)

        flag_summaries.append(
            ActiveRiskFlagSummary(
                flag_id=int(getattr(f, "flag_id")),
                date=flag_date_str,
                route_id=int(flag_route_id) if flag_route_id is not None else None,
                corridor=corridor_str,
                risk_level=str(lvl),
                reason=str(getattr(f, "reason", "") or "No specific disruption rationale recorded"),
                is_active=bool(getattr(f, "is_active", True)),
            )
        )

    # 3. Fetch baseline macro metrics (volatility, drawdowns)
    try:
        macro_eval = evaluate_market_risk(eval_date=today, db=db, persist_flag=False)
        macro_metrics = macro_eval.get("metrics", {})
        macro_level = (macro_eval.get("risk_level") or "calm").lower()
    except Exception:
        macro_metrics = {}
        macro_level = "calm"

    # 4. Synthesize hierarchical sentiment and plain-language summary
    if has_high or macro_level == "high":
        overall_sentiment = "high"
        high_flags_count = sum(1 for f in flag_summaries if f.risk_level == "high")
        summary_reason = (
            f"High Risk Alert: {high_flags_count} corridor(s) experiencing critical disruption events "
            f"or extreme market volatility. Exercise maximum chartering caution."
        )
    elif has_elevated or macro_level == "elevated":
        overall_sentiment = "elevated"
        elevated_flags_count = sum(1 for f in flag_summaries if f.risk_level in ("elevated", "high"))
        summary_reason = (
            f"Elevated Market Risk: {elevated_flags_count} corridor(s) under caution due to regional congestion "
            f"or heightened freight rate volatility."
        )
    else:
        overall_sentiment = "calm"
        summary_reason = (
            "All 8 monitored overseas shipping corridors operating under normal risk conditions. "
            "Zero active disruption flags."
        )

    return MarketWatchResponse(
        as_of_date=today.isoformat(),
        overall_sentiment=overall_sentiment,
        summary_reason=summary_reason,
        active_flags_count=len(flag_summaries),
        active_flags=flag_summaries,
        macro_metrics=macro_metrics,
    )


@router.post(
    "/action",
    response_model=ActionDecisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Layer 2: Mark Recommendation as Actioned",
)
def mark_decision_as_actioned(
    req: ActionDecisionRequest,
    db: Session = Depends(get_db),
):
    """
    Module F Layer 2 — Mark as Actioned.
    Accepts a decision_id, validates it exists in DecisionRecommendations,
    and logs an anonymous, timestamped ActionedDecisions record.
    (No user authentication attached, consistent with blueprint design).
    """
    decision = (
        db.query(DecisionRecommendation)
        .filter(DecisionRecommendation.decision_id == req.decision_id)
        .first()
    )
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision recommendation #{req.decision_id} not found in database.",
        )

    action_record = ActionedDecision(
        decision_id=req.decision_id,
        actioned_at=datetime.now(timezone.utc),
        note=req.note,
    )
    db.add(action_record)
    db.commit()
    db.refresh(action_record)

    action_dt = getattr(action_record, "actioned_at", None)
    actioned_at_str = (
        action_dt.isoformat()
        if hasattr(action_dt, "isoformat")
        else str(action_dt or datetime.now(timezone.utc).isoformat())
    )

    return ActionDecisionResponse(
        status="success",
        action_id=int(getattr(action_record, "action_id")),
        decision_id=int(getattr(action_record, "decision_id")),
        actioned_at=actioned_at_str,
        note=getattr(action_record, "note", None),
    )
