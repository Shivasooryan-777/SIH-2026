"""
Reference Master Data API Endpoints Test Suite
==============================================
Verifies read-only reference data endpoints:
- GET /api/ports: 14 ports, valid schemas, origin/destination roles
- GET /api/vessel-types: 4 vessel size classes, physical parameters
- GET /api/routes: 8 shipping lanes with resolved port names & countries
"""

import sys
from pathlib import Path
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.main import app

client = TestClient(app)


def test_get_ports_endpoint():
    """Verify GET /api/ports returns all 14 ports with valid schema."""
    response = client.get("/api/ports")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    ports = response.json()
    assert isinstance(ports, list)
    assert len(ports) == 14, f"Expected 14 ports, got {len(ports)}"

    roles = {p["port_role"] for p in ports}
    assert "origin" in roles
    assert "destination" in roles

    destinations = [p for p in ports if p["port_role"] == "destination"]
    origins = [p for p in ports if p["port_role"] == "origin"]
    assert len(destinations) == 7, f"Expected 7 destinations, got {len(destinations)}"
    assert len(origins) == 7, f"Expected 7 origins, got {len(origins)}"

    for p in ports:
        assert "port_id" in p and isinstance(p["port_id"], int)
        assert "name" in p and isinstance(p["name"], str) and len(p["name"]) > 0
        assert "country" in p and isinstance(p["country"], str)
        assert "max_loa_m" in p and p["max_loa_m"] > 0
        assert "max_beam_m" in p and p["max_beam_m"] > 0
        assert "baseline_draft_m" in p and p["baseline_draft_m"] > 0


def test_get_vessel_types_endpoint():
    """Verify GET /api/vessel-types returns all 4 classes in scope."""
    response = client.get("/api/vessel-types")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    vessels = response.json()
    assert isinstance(vessels, list)
    assert len(vessels) == 4, f"Expected 4 vessel classes, got {len(vessels)}"

    expected_names = {"Handysize", "Supramax", "Panamax", "Capesize"}
    names = {v["name"] for v in vessels}
    assert names == expected_names, f"Expected {expected_names}, got {names}"

    for v in vessels:
        assert v["min_dwt"] < v["max_dwt"]
        assert v["required_draft_m"] > 0
        assert v["standard_speed_knots"] > 0
        assert v["fuel_curve_coef"] > 0


def test_get_routes_endpoint_with_resolved_port_names():
    """Verify GET /api/routes returns all 8 corridors with resolved port names."""
    response = client.get("/api/routes")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    routes = response.json()
    assert isinstance(routes, list)
    assert len(routes) == 8, f"Expected 8 routes, got {len(routes)}"

    for r in routes:
        assert "route_id" in r and isinstance(r["route_id"], int)
        assert "origin_port_id" in r and isinstance(r["origin_port_id"], int)
        assert "origin_port_name" in r and len(r["origin_port_name"]) > 0
        assert "origin_country" in r and len(r["origin_country"]) > 0
        assert "destination_port_id" in r and isinstance(r["destination_port_id"], int)
        assert "destination_port_name" in r and len(r["destination_port_name"]) > 0
        assert "destination_country" in r and len(r["destination_country"]) > 0
        assert "distance_nm" in r and r["distance_nm"] > 0
        assert "typical_transit_days" in r and r["typical_transit_days"] > 0
