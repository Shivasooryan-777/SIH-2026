"""
FastAPI Application Skeleton
============================
Intelligent Freight Forecasting & Vessel Chartering Decision Support System
SIH 2026 | Problem Statement ID: SIH26006 | Ministry of Steel
"""

import logging
from fastapi import FastAPI, Depends, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.api.forecast import router as forecast_router
from backend.app.api.port_matching import router as port_matching_router
from backend.app.api.risk_radar import router as risk_radar_router
from backend.app.api.decision import router as decision_router
from backend.app.api.idle_contract import router as idle_contract_router
from backend.app.api.interaction import router as interaction_router

logger = logging.getLogger("backend_api")

app = FastAPI(
    title="Intelligent Freight Forecasting & Decision Support System",
    description="SIH 2026 | Ministry of Steel | Problem Statement SIH26006",
    version="0.1.0",
)

# Enable CORS for local frontend development (React + Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint confirming API and database connectivity.
    Security Notice:
    - Verifies connectivity by executing 'SELECT 1'.
    - NEVER returns or exposes the database connection string, host, or credentials.
    """
    try:
        result = db.execute(text("SELECT 1")).scalar()
        if result == 1:
            return {"status": "healthy", "database": "connected"}
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "database": "unexpected_query_result"},
        )
    except Exception as exc:
        logger.error("Health check database query failed: %s", type(exc).__name__)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "database": "disconnected"},
        )


# Mount the 6 module routers under /api
app.include_router(forecast_router, prefix="/api")
app.include_router(port_matching_router, prefix="/api")
app.include_router(risk_radar_router, prefix="/api")
app.include_router(decision_router, prefix="/api")
app.include_router(idle_contract_router, prefix="/api")
app.include_router(interaction_router, prefix="/api")


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Intelligent Freight Forecasting & Vessel Chartering Decision Support System API",
        "docs_url": "/docs",
        "health_url": "/api/health",
    }
