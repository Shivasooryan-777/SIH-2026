"""
Module E — Idle-Time & Contract Structuring API Router
======================================================
E1: Spot-vs-period contract structuring recommendation based on trough detection.
E2: Speed & fuel optimization advisory (Just-In-Time arrival) for vessels in transit.

(Implementation scheduled for subsequent sessions)
"""

from fastapi import APIRouter

router = APIRouter(prefix="/idle-contract", tags=["Module E — Idle-Time & Contract Structuring"])


@router.get("/")
def get_idle_contract_status():
    """Stub endpoint for Module E Idle-Time & Contract Structuring status."""
    return {
        "module": "E — Idle-Time & Contract Structuring",
        "status": "ready_for_session",
        "description": "E1 Spot-vs-period structuring and E2 Speed & fuel optimization advisory (JIT)",
    }
