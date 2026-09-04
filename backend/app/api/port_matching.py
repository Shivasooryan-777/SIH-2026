"""
Module B — Port-Matching Engine API Router
==========================================
Exposes endpoints to evaluate vessel size class compatibility against destination port
constraints under dynamic, season-adjusted draft conditions.
"""

from datetime import date as DateType, datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import Port
from backend.app.services.port_matching import (
    evaluate_port_compatibility,
    effective_draft,
    is_compatible,
)

router = APIRouter(prefix="/port-matching", tags=["Module B — Port-Matching Engine"])


class PortMatchingRequest(BaseModel):
    port_id: Optional[int] = Field(None, description="Port ID to evaluate")
    port_name: Optional[str] = Field(None, description="Port name (e.g. Paradip_Inner, Dhamra)")
    date: Optional[str] = Field(None, description="Date (YYYY-MM-DD, defaults to today)")
    cargo_volume_tons: Optional[int] = Field(None, description="Cargo volume in metric tons")


@router.get("/")
def get_port_matching_status():
    """Returns Module B Port-Matching Engine status."""
    return {
        "module": "B — Port-Matching Engine",
        "status": "active",
        "description": "Dynamic vessel-to-port compatibility based on seasonal draft, LOA, and beam constraints",
    }


@router.get("/evaluate")
def evaluate_port_matching_get(
    port_name: Optional[str] = Query(None, description="Port name"),
    port_id: Optional[int] = Query(None, description="Port ID"),
    date_str: Optional[str] = Query(None, alias="date", description="Date YYYY-MM-DD (defaults to today)"),
    cargo_volume: Optional[int] = Query(None, alias="cargo_volume_tons", description="Cargo volume in metric tons"),
    db: Session = Depends(get_db),
):
    """
    Evaluate port-vessel compatibility for a port on a given date.
    Returns ranked compatible vessel classes (largest-safe-first).
    """
    if not port_id and not port_name:
        raise HTTPException(status_code=400, detail="Must provide either port_id or port_name")

    query = db.query(Port)
    if port_id:
        port = query.filter(Port.port_id == port_id).first()
    else:
        port = query.filter(Port.name == port_name).first()

    if not port:
        raise HTTPException(status_code=404, detail=f"Port not found: {port_id or port_name}")

    eval_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.now(timezone.utc).date()

    return evaluate_port_compatibility(
        port=port,
        eval_date=eval_date,
        db=db,
        cargo_volume_tons=cargo_volume,
    )


@router.post("/evaluate")
def evaluate_port_matching_post(
    req: PortMatchingRequest,
    db: Session = Depends(get_db),
):
    """
    Evaluate port-vessel compatibility via POST body.
    """
    if not req.port_id and not req.port_name:
        raise HTTPException(status_code=400, detail="Must provide either port_id or port_name")

    query = db.query(Port)
    if req.port_id:
        port = query.filter(Port.port_id == req.port_id).first()
    else:
        port = query.filter(Port.name == req.port_name).first()

    if not port:
        raise HTTPException(status_code=404, detail=f"Port not found: {req.port_id or req.port_name}")

    eval_date = datetime.strptime(req.date, "%Y-%m-%d").date() if req.date else datetime.now(timezone.utc).date()

    return evaluate_port_compatibility(
        port=port,
        eval_date=eval_date,
        db=db,
        cargo_volume_tons=req.cargo_volume_tons,
    )
