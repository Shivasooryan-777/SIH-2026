"""
Database Schema Verification Test
=================================
Confirms all 15 tables and their columns defined in docs/blueprint.md Section 8
exist in the live Neon Postgres database with the exact required schema.
"""

import sys
from pathlib import Path
import pytest
from sqlalchemy import inspect

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.database import engine
from backend.database.migrate import EXPECTED_TABLES, run_migration


# Table-to-columns mapping matching docs/blueprint.md Section 8 exactly
EXPECTED_SCHEMA = {
    # 8.1 Reference / Master Data Tables
    "ports": {
        "columns": [
            "port_id", "name", "country", "port_role",
            "max_loa_m", "max_beam_m", "baseline_draft_m",
            "latitude", "longitude",
        ],
        "nullable_cols": {"latitude", "longitude"},
    },
    "vessel_types": {
        "columns": [
            "vessel_type_id", "name", "min_dwt", "max_dwt",
            "required_draft_m", "typical_loa_m", "typical_beam_m",
            "standard_speed_knots", "fuel_curve_coef",
        ],
        "nullable_cols": set(),
    },
    "routes": {
        "columns": [
            "route_id", "origin_port_id", "destination_port_id",
            "distance_nm", "typical_transit_days",
        ],
        "nullable_cols": set(),
    },

    # 8.2 Ingested Time-Series / Reference Data Tables
    "freight_rate_data": {
        "columns": [
            "rate_id", "date", "vessel_type_id",
            "index_type", "value_usd_per_day", "source",
        ],
        "nullable_cols": {"vessel_type_id"},
    },
    "macro_indicators": {
        "columns": [
            "indicator_id", "date", "indicator_type", "value",
        ],
        "nullable_cols": set(),
    },
    "port_draft_advisory": {
        "columns": [
            "advisory_id", "port_id", "date", "available_draft_m", "season_tag",
        ],
        "nullable_cols": {"season_tag"},
    },
    "risk_events": {
        "columns": [
            "event_id", "date", "event_type", "description",
            "affected_route_id", "severity_level", "historical_price_impact_pct",
        ],
        "nullable_cols": {"affected_route_id", "historical_price_impact_pct"},
    },

    # 8.3 Workflow / Request-Driven Tables
    "cargo_requests": {
        "columns": [
            "request_id", "created_at", "cargo_type", "cargo_volume_tons",
            "origin_port_id", "destination_port_id",
            "desired_timeframe_days", "desired_contract_pref",
        ],
        "nullable_cols": {"desired_contract_pref"},
    },
    "forecast_results": {
        "columns": [
            "forecast_id", "request_id", "generated_at",
            "vessel_type_id", "p10_price", "p50_price", "p90_price", "model_version",
        ],
        "nullable_cols": {"vessel_type_id"},
    },
    "shap_explanations": {
        "columns": [
            "explanation_id", "forecast_id", "feature_name",
            "contribution_pct", "direction",
        ],
        "nullable_cols": set(),
    },
    "risk_flags": {
        "columns": [
            "flag_id", "date", "route_id", "risk_level", "reason", "is_active",
        ],
        "nullable_cols": {"route_id"},
    },

    # 8.4 Recommendation & Action-Logging Tables
    "decision_recommendations": {
        "columns": [
            "decision_id", "request_id", "recommended_vessel_type_id",
            "recommended_action", "expected_price", "expected_savings_usd", "generated_at",
        ],
        "nullable_cols": set(),
    },
    "idle_time_analysis": {
        "columns": [
            "analysis_id", "request_id", "recommended_contract_type",
            "forecasted_trough_start", "forecasted_trough_end", "estimated_cost_saved_usd",
        ],
        "nullable_cols": {"forecasted_trough_start", "forecasted_trough_end", "estimated_cost_saved_usd"},
    },
    "speed_optimization_log": {
        "columns": [
            "speed_id", "request_id", "route_id", "standard_speed_knots",
            "recommended_speed_knots", "port_congestion_hours",
            "fuel_saved_tons", "co2_reduced_kg",
        ],
        "nullable_cols": set(),
    },
    "actioned_decisions": {
        "columns": [
            "action_id", "decision_id", "actioned_at", "note",
        ],
        "nullable_cols": {"note"},
    },
}


def test_migration_execution():
    """Verify that migration runs cleanly and returns True."""
    migration_success = run_migration()
    assert migration_success is True, "Database migration failed to execute cleanly."


def test_all_15_tables_exist():
    """Verify that exactly the 15 expected tables exist in the database."""
    inspector = inspect(engine)
    live_tables = set(inspector.get_table_names())

    for expected_table in EXPECTED_TABLES:
        assert expected_table in live_tables, f"Table '{expected_table}' missing from database!"


@pytest.mark.parametrize("table_name,spec", EXPECTED_SCHEMA.items())
def test_table_columns_and_nullability(table_name, spec):
    """Verify that each table contains the exact columns with correct nullability."""
    inspector = inspect(engine)
    columns_info = inspector.get_columns(table_name)
    assert len(columns_info) > 0, f"Table '{table_name}' has no columns!"

    live_col_names = {c["name"] for c in columns_info}
    expected_col_names = set(spec["columns"])

    # Check for missing columns
    missing_cols = expected_col_names - live_col_names
    assert not missing_cols, f"Table '{table_name}' missing expected columns: {missing_cols}"

    # Check for unauthorized extra columns
    extra_cols = live_col_names - expected_col_names
    assert not extra_cols, f"Table '{table_name}' has unexpected extra columns: {extra_cols}"

    # Check nullability constraints
    nullable_cols = spec["nullable_cols"]
    for c in columns_info:
        col_name = c["name"]
        is_nullable = c["nullable"]
        if col_name in nullable_cols:
            assert is_nullable is True, f"Column '{table_name}.{col_name}' should be nullable"
        else:
            # Note: primary key columns are always not nullable
            assert is_nullable is False, f"Column '{table_name}.{col_name}' should NOT be nullable"
