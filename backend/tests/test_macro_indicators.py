"""
Macro Indicators Ingestion & Database Test Suite
================================================
Verifies:
1. Data-quality checks on ingested macro indicator series (Brent crude, USD/INR, coal futures)
2. Proper shaping to MacroIndicators schema: (date, indicator_type, value)
3. Successful insertion into Neon database
4. Strict idempotency of database seeding (running twice adds zero duplicate rows)
"""

import sys
from pathlib import Path
import pytest
import pandas as pd

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.database import SessionLocal
from backend.app.models import MacroIndicator
from backend.ingestion.macro_indicators import (
    DEFAULT_PROCESSED_OUTPUT_PATH,
    MACRO_TICKERS,
    fetch_indicator_series,
    seed_macro_indicators_to_db,
)


@pytest.fixture(scope="module")
def db_session():
    """Module-scoped database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_processed_macro_csv_exists_and_valid():
    """Verify that processed macro CSV exists and meets data quality standards."""
    csv_path = DEFAULT_PROCESSED_OUTPUT_PATH
    assert csv_path.exists(), f"Processed macro CSV not found at {csv_path}"

    df = pd.read_csv(csv_path)
    assert not df.empty, "Processed macro indicators CSV is empty!"

    required_cols = {"date", "indicator_type", "value"}
    assert required_cols.issubset(set(df.columns)), f"Missing required columns in CSV: {df.columns}"

    # No null values
    assert df["date"].isnull().sum() == 0, "Found null dates in macro series"
    assert df["value"].isnull().sum() == 0, "Found null values in macro series"
    assert df["indicator_type"].isnull().sum() == 0, "Found null indicator types"

    # All expected indicator types present
    expected_types = set(MACRO_TICKERS.keys())
    present_types = set(df["indicator_type"].unique())
    assert expected_types == present_types, f"Expected types {expected_types}, got {present_types}"

    # Positive values
    assert (df["value"] > 0).all(), "Found non-positive values in macro series"

    # Check chronological ordering per indicator
    for ind in expected_types:
        ind_df = df[df["indicator_type"] == ind].reset_index(drop=True)
        dates = ind_df["date"].tolist()
        assert dates == sorted(dates), f"Dates not strictly sorted for indicator '{ind}'"
        assert len(dates) == len(set(dates)), f"Duplicate dates found for indicator '{ind}'"


def test_macro_indicators_in_database(db_session):
    """Verify macro indicators table in Neon contains valid ingested data."""
    count = db_session.query(MacroIndicator).count()
    assert count > 0, "No records found in Neon 'macro_indicators' table!"

    # Verify each indicator type is present in database
    for ind in MACRO_TICKERS.keys():
        ind_count = db_session.query(MacroIndicator).filter(MacroIndicator.indicator_type == ind).count()
        assert ind_count > 0, f"No records found in database for indicator '{ind}'"

    # Verify sample record integrity
    sample = db_session.query(MacroIndicator).first()
    assert sample.date is not None
    assert sample.indicator_type in MACRO_TICKERS
    assert sample.value > 0


def test_macro_indicators_idempotency(db_session):
    """Verify that re-seeding macro indicators into database inserts 0 duplicates."""
    initial_count = db_session.query(MacroIndicator).count()

    # Load from processed CSV
    df = pd.read_csv(DEFAULT_PROCESSED_OUTPUT_PATH)
    inserted, skipped = seed_macro_indicators_to_db(df)

    new_count = db_session.query(MacroIndicator).count()

    assert inserted == 0, f"Expected 0 new insertions on re-run, got {inserted}"
    assert new_count == initial_count, (
        f"Idempotency violation! Count changed from {initial_count} to {new_count}"
    )
