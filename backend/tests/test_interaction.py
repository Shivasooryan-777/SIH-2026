"""
Module F — Interaction Layer Test Suite
========================================
Tests:
1. Layer 1: Always-On Market Watch status under calm baseline conditions.
2. Layer 1: Always-On Market Watch status with active corridor risk flags.
3. Layer 2: Mark as Actioned decision logging with valid decision_id.
4. Layer 2: Mark as Actioned error handling on non-existent decision_id.
"""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.database import SessionLocal
from backend.app.main import app
from backend.app.models import (
    ActionedDecision,
    CargoRequest,
    DecisionRecommendation,
    Port,
    RiskFlag,
    Route,
    VesselType,
)

client = TestClient(app)


@pytest.fixture(scope="function")
def db_session():
    """Function-scoped database session with clean rollback."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_interaction_status_endpoint():
    """Verify /api/interaction/ root endpoint reports active status and registered routes."""
    response = client.get("/api/interaction/")
    assert response.status_code == 200
    data = response.json()
    assert data.get("module") == "F — Interaction Layer"
    assert data.get("status") == "active"
    assert len(data.get("endpoints", [])) >= 2


def test_market_watch_calm_baseline(db_session):
    """
    Verify Layer 1 Always-On Market Watch returns valid payload with zero parameters.
    When no high/elevated flags are active, returns calm baseline sentiment.
    """
    # Deactivate existing active flags temporarily for clean baseline test
    db_session.query(RiskFlag).filter(RiskFlag.is_active == True).update({"is_active": False})
    db_session.commit()

    response = client.get("/api/interaction/market-watch")
    assert response.status_code == 200
    data = response.json()

    assert "as_of_date" in data
    assert "overall_sentiment" in data
    assert "summary_reason" in data
    assert "active_flags" in data
    assert "macro_metrics" in data

    assert data["active_flags_count"] == 0
    assert len(data["active_flags"]) == 0
    assert data["overall_sentiment"] in ("calm", "elevated", "high")
    assert len(data["summary_reason"]) > 10


def test_market_watch_with_active_flags(db_session):
    """
    Verify Layer 1 Always-On Market Watch correctly elevates overall sentiment,
    resolves corridor origin/destination names, and includes active flags.
    """
    route = db_session.query(Route).filter(Route.route_id == 1).first()
    assert route is not None, "Route #1 required for corridor resolution test"

    # Insert a high-severity test RiskFlag
    flag = RiskFlag(
        date=datetime.now(timezone.utc).date(),
        route_id=1,
        risk_level="high",
        reason="Severe Weather: Cyclone alert along Paradip approach corridor",
        is_active=True,
    )
    db_session.add(flag)
    db_session.commit()
    db_session.refresh(flag)

    try:
        response = client.get("/api/interaction/market-watch")
        assert response.status_code == 200
        data = response.json()

        assert data["overall_sentiment"] == "high"
        assert data["active_flags_count"] >= 1

        # Check corridor resolution (e.g. Taboneo -> Haldia)
        flag_entry = next((f for f in data["active_flags"] if f["flag_id"] == flag.flag_id), None)
        assert flag_entry is not None
        assert "->" in flag_entry["corridor"]
        assert flag_entry["risk_level"] == "high"
        assert "Cyclone alert" in flag_entry["reason"]
        assert "High Risk Alert" in data["summary_reason"]
    finally:
        # Clean up test flag
        db_session.delete(flag)
        db_session.commit()


def test_mark_as_actioned_success(db_session):
    """
    Verify Layer 2 POST /api/interaction/action creates an anonymous,
    timestamped ActionedDecision record linked to a valid DecisionRecommendation.
    """
    # Look up required foreign key reference entities
    origin = db_session.query(Port).first()
    dest = db_session.query(Port).filter(Port.port_id != origin.port_id).first()
    vessel = db_session.query(VesselType).first()
    assert origin and dest and vessel

    # Clean up any leftover test rows from previously aborted runs
    stale_actions = db_session.query(ActionedDecision).filter(ActionedDecision.note == "Fixture confirmed with chartering desk manager").all()
    for sa in stale_actions:
        db_session.delete(sa)
    db_session.flush()

    # Create dummy CargoRequest & DecisionRecommendation
    req = CargoRequest(
        cargo_type="coking_coal",
        cargo_volume_tons=75000,
        origin_port_id=origin.port_id,
        destination_port_id=dest.port_id,
        desired_timeframe_days=30,
        desired_contract_pref="spot",
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)

    dec = DecisionRecommendation(
        request_id=req.request_id,
        recommended_vessel_type_id=vessel.vessel_type_id,
        recommended_action="fix_now",
        expected_price=Decimal("18.50"),
        expected_savings_usd=Decimal("0.00"),
    )
    db_session.add(dec)
    db_session.commit()
    db_session.refresh(dec)

    try:
        # Post action log
        payload = {
            "decision_id": dec.decision_id,
            "note": "Fixture confirmed with chartering desk manager",
        }
        response = client.post("/api/interaction/action", json=payload)
        assert response.status_code == 201
        data = response.json()

        assert data["status"] == "success"
        assert data["decision_id"] == dec.decision_id
        assert data["note"] == "Fixture confirmed with chartering desk manager"
        assert "actioned_at" in data
        assert data["action_id"] > 0

        # Verify persisted record in live DB
        persisted = (
            db_session.query(ActionedDecision)
            .filter(ActionedDecision.action_id == data["action_id"])
            .first()
        )
        assert persisted is not None
        assert persisted.decision_id == dec.decision_id
        assert persisted.note == "Fixture confirmed with chartering desk manager"
    finally:
        # Clean up test rows in strict reverse foreign-key dependency order
        action_rows = (
            db_session.query(ActionedDecision)
            .filter(ActionedDecision.decision_id == dec.decision_id)
            .all()
        )
        for ar in action_rows:
            db_session.delete(ar)
        db_session.flush()

        db_session.delete(dec)
        db_session.flush()

        db_session.delete(req)
        db_session.commit()


def test_mark_as_actioned_invalid_decision_id():
    """
    Verify Layer 2 POST /api/interaction/action rejects non-existent decision_id
    with HTTP 404 Not Found.
    """
    payload = {
        "decision_id": 99999999,
        "note": "Should fail due to invalid decision_id",
    }
    response = client.post("/api/interaction/action", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json().get("detail", "").lower()
