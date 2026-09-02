"""
FastAPI Health Check and Route Stubs Test Suite
===============================================
Tests health endpoint, DB connectivity, and all 6 module route stubs.
Confirms no connection strings or secrets are leaked.
"""

import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify root endpoint responds with basic API discovery info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "health_url" in data
    assert "docs_url" in data


def test_health_check_endpoint():
    """Verify /health confirms DB connectivity and returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "healthy"
    assert data.get("database") == "connected"


def test_api_health_check_endpoint():
    """Verify /api/health confirms DB connectivity and returns healthy status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "healthy"
    assert data.get("database") == "connected"


def test_health_check_security_no_leaked_credentials():
    """Verify neither /health nor /api/health leaks credentials or connection strings."""
    for path in ["/health", "/api/health"]:
        response = client.get(path)
        content_text = response.text.lower()
        for sensitive_keyword in ["password", "postgres://", "postgresql://", "@ep-", "neon.tech"]:
            assert sensitive_keyword not in content_text, f"Potential credential leak in {path}!"


def test_all_six_module_route_stubs():
    """Verify each of the 6 module route stubs is registered and reachable."""
    module_endpoints = {
        "/api/forecast/": "A — Forecast Engine",
        "/api/port-matching/": "B — Port-Matching Engine",
        "/api/risk-radar/": "C — Risk Radar",
        "/api/decision/": "D — Decision Engine",
        "/api/idle-contract/": "E — Idle-Time & Contract Structuring",
        "/api/interaction/": "F — Interaction Layer",
    }

    for endpoint, expected_module_name in module_endpoints.items():
        response = client.get(endpoint)
        assert response.status_code == 200, f"Module stub {endpoint} returned status {response.status_code}"
        data = response.json()
        assert "module" in data
        assert expected_module_name in data["module"]
        assert "status" in data
