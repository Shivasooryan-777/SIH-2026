"""
Database Migration Script
=========================
Creates and verifies all 15 tables from docs/blueprint.md in the Neon database.
Idempotent and safe to run multiple times.

SECURITY NOTICE:
Never prints or logs the DATABASE_URL or database credentials.
"""

import sys
import logging
from sqlalchemy import inspect
from backend.app.database import engine, Base
# Import models to register them with Base.metadata
import backend.app.models  # noqa: F401

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("db_migration")

EXPECTED_TABLES = [
    # 8.1 Reference / Master Data
    "ports",
    "vessel_types",
    "routes",
    # 8.2 Ingested Time-Series / Reference
    "freight_rate_data",
    "macro_indicators",
    "port_draft_advisory",
    "risk_events",
    # 8.3 Workflow / Request-Driven
    "cargo_requests",
    "forecast_results",
    "shap_explanations",
    "risk_flags",
    # 8.4 Recommendation & Action-Logging
    "decision_recommendations",
    "idle_time_analysis",
    "speed_optimization_log",
    "actioned_decisions",
]


def run_migration() -> bool:
    """
    Execute Base.metadata.create_all against the configured database engine
    and verify that all 15 expected tables exist.
    """
    logger.info("Starting schema migration against configured database...")

    try:
        # Create all tables declared in models.py
        Base.metadata.create_all(bind=engine)
        logger.info("DDL execution complete. Verifying schema...")

        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())

        missing_tables = [t for t in EXPECTED_TABLES if t not in existing_tables]

        if missing_tables:
            logger.error("Migration incomplete. Missing tables: %s", missing_tables)
            return False

        logger.info("Verification SUCCESS: All %d expected tables exist in database.", len(EXPECTED_TABLES))
        for tbl in sorted(EXPECTED_TABLES):
            col_count = len(inspector.get_columns(tbl))
            logger.info("  ✓ Table '%s' verified (%d columns)", tbl, col_count)

        return True

    except Exception as exc:
        logger.error("Migration failed with error: %s", type(exc).__name__, exc_info=True)
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
