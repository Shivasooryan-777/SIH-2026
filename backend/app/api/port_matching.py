"""
Module B — Port-Matching Engine API Router
==========================================
Determines vessel size class compatibility against destination port constraints
under current season-adjusted dynamic draft conditions.

(Implementation scheduled for subsequent sessions)
"""

from fastapi import APIRouter

router = APIRouter(prefix="/port-matching", tags=["Module B — Port-Matching Engine"])


@router.get("/")
def get_port_matching_status():
    """Stub endpoint for Module B Port-Matching Engine status."""
    return {
        "module": "B — Port-Matching Engine",
        "status": "ready_for_session",
        "description": "Dynamic vessel-to-port compatibility ranking (Handysize, Supramax, Panamax, Capesize)",
    }
