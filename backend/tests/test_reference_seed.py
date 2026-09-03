"""
Reference Data Seeding Test Suite
=================================
Verifies reference data seeding in Neon Postgres:
1. Exact expected row counts per table (Ports=14, VesselTypes=4, Routes=8, RiskEvents=4)
2. Foreign key integrity resolution (Route origin/destination -> Ports, RiskEvent affected_route -> Routes)
3. Non-null constraints on all loaded data
4. Strict idempotency (re-running seed yields identical row counts with zero duplicate rows)
"""

import sys
from pathlib import Path
import pytest

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.database import SessionLocal
from backend.app.models import Port, VesselType, Route, RiskEvent
from backend.database.seed_reference_data import seed_all_reference_data

EXPECTED_COUNTS = {
    "ports": 14,
    "vessel_types": 4,
    "routes": 8,
    "risk_events": 4,
}


@pytest.fixture(scope="module")
def db_session():
    """Module-scoped database session for verification."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_seed_execution_and_counts(db_session):
    """
    Run seeding function and assert exact expected row counts in Neon database.
    """
    counts = seed_all_reference_data()

    assert counts["ports"] == EXPECTED_COUNTS["ports"], (
        f"Expected {EXPECTED_COUNTS['ports']} ports, got {counts['ports']}"
    )
    assert counts["vessel_types"] == EXPECTED_COUNTS["vessel_types"], (
        f"Expected {EXPECTED_COUNTS['vessel_types']} vessel types, got {counts['vessel_types']}"
    )
    assert counts["routes"] == EXPECTED_COUNTS["routes"], (
        f"Expected {EXPECTED_COUNTS['routes']} routes, got {counts['routes']}"
    )
    assert counts["risk_events"] == EXPECTED_COUNTS["risk_events"], (
        f"Expected {EXPECTED_COUNTS['risk_events']} risk events, got {counts['risk_events']}"
    )


def test_ports_data_integrity(db_session):
    """Verify ports master data content and constraints."""
    ports = db_session.query(Port).all()
    assert len(ports) == 14

    destinations = [p for p in ports if p.port_role == "destination"]
    origins = [p for p in ports if p.port_role == "origin"]

    assert len(destinations) == 7, f"Expected 7 destination ports, got {len(destinations)}"
    assert len(origins) == 7, f"Expected 7 origin ports, got {len(origins)}"

    for p in ports:
        assert p.name and len(p.name) > 0
        assert p.country and len(p.country) > 0
        assert p.max_loa_m > 0
        assert p.max_beam_m > 0
        assert p.baseline_draft_m > 0


def test_vessel_types_data_integrity(db_session):
    """Verify vessel types master data content and constraints."""
    vessels = db_session.query(VesselType).all()
    assert len(vessels) == 4

    expected_names = {"Handysize", "Supramax", "Panamax", "Capesize"}
    actual_names = {v.name for v in vessels}
    assert actual_names == expected_names

    for v in vessels:
        assert v.min_dwt < v.max_dwt
        assert v.required_draft_m > 0
        assert v.typical_loa_m > 0
        assert v.typical_beam_m > 0
        assert v.standard_speed_knots > 0
        assert v.fuel_curve_coef > 0


def test_routes_foreign_keys_resolve(db_session):
    """
    Spot-check that foreign keys resolve:
    Every route's origin_port_id and destination_port_id must exist in ports table.
    """
    routes = db_session.query(Route).all()
    assert len(routes) == 8

    all_port_ids = {p.port_id for p in db_session.query(Port.port_id).all()}

    for r in routes:
        assert r.origin_port_id in all_port_ids, (
            f"Route {r.route_id} references invalid origin_port_id {r.origin_port_id}"
        )
        assert r.destination_port_id in all_port_ids, (
            f"Route {r.route_id} references invalid destination_port_id {r.destination_port_id}"
        )
        assert r.distance_nm > 0
        assert r.typical_transit_days > 0


def test_risk_events_foreign_keys_resolve(db_session):
    """
    Spot-check that risk events resolve properly:
    If affected_route_id is present, it must exist in the routes table.
    """
    events = db_session.query(RiskEvent).all()
    assert len(events) == 4

    all_route_ids = {r.route_id for r in db_session.query(Route.route_id).all()}

    linked_events = 0
    global_events = 0

    for e in events:
        assert e.date is not None
        assert e.event_type and len(e.event_type) > 0
        assert e.description and len(e.description) > 0
        assert e.severity_level in {"low", "medium", "high"}

        if e.affected_route_id is not None:
            assert e.affected_route_id in all_route_ids, (
                f"RiskEvent {e.event_id} references non-existent route_id {e.affected_route_id}"
            )
            linked_events += 1
        else:
            global_events += 1

    assert linked_events == 3, f"Expected 3 route-specific risk events, got {linked_events}"
    assert global_events == 1, f"Expected 1 market-wide risk event, got {global_events}"


def test_seeding_idempotency(db_session):
    """
    Confirm running seed_all_reference_data twice does NOT create duplicates.
    """
    counts_run1 = {
        "ports": db_session.query(Port).count(),
        "vessel_types": db_session.query(VesselType).count(),
        "routes": db_session.query(Route).count(),
        "risk_events": db_session.query(RiskEvent).count(),
    }

    # Run seeding again
    counts_run2 = seed_all_reference_data()

    assert counts_run2 == counts_run1, (
        f"Idempotency violation! Row counts changed on second seed run: {counts_run1} -> {counts_run2}"
    )
