"""
Module A — Forecast Engine API Router
======================================
Predicts near-term freight rate ranges (P10/P50/P90) per vessel type per route,
with SHAP feature attributions explaining contributing factors.

(Full ML inference implementation scheduled for Session 4)
"""

from fastapi import APIRouter

router = APIRouter(prefix="/forecast", tags=["Module A — Forecast Engine"])


@router.get("/")
def get_forecast_status():
    """Stub endpoint for Module A Forecast Engine status."""
    return {
        "module": "A — Forecast Engine",
        "status": "ready_for_session_4",
        "description": "P10/P50/P90 quantile price band forecasts and SHAP feature attributions",
    }
