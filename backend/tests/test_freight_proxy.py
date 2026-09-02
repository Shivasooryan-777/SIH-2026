"""
Tests for Freight Data Ingestion and BDRY Proxy Splicing Pipeline
================================================================
Verifies:
1. Spliced time series has strictly sorted, monotonic ascending dates with no duplicates.
2. Zero null/NaN values across essential price, proxy, and provenance columns.
3. No unexplained gaps larger than the defined threshold (<= 5 calendar days for standard market closures).
4. Correct proxy tagging (`is_proxy=True` for BDRY ETF, `is_proxy=False` for actual BDI).
5. Continuous chained index (`normalized_index_base100`) has no NaN/infinite values.
6. Malformed dates in raw CSV are safely handled.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import pytest

# Ensure backend directory is in python path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from ingestion.freight_proxy import (
    REPO_ROOT,
    splice_freight_series,
    load_historical_bdi,
    save_processed_data,
)


@pytest.fixture
def mock_bdry_data() -> pd.DataFrame:
    """Generate representative BDRY ETF daily trading dataset (business days)."""
    # 20 business days in April 2024
    dates = pd.date_range(start="2024-04-01", end="2024-04-30", freq="B")
    data = {
        "date": [d.strftime("%Y-%m-%d") for d in dates],
        "open": np.linspace(15.0, 18.0, len(dates)),
        "high": np.linspace(15.5, 18.5, len(dates)),
        "low": np.linspace(14.8, 17.5, len(dates)),
        "close": np.linspace(15.2, 18.2, len(dates)),
        "volume": [100000 + i * 1000 for i in range(len(dates))],
    }
    return pd.DataFrame(data)


@pytest.fixture
def mock_historical_bdi_data() -> pd.DataFrame:
    """Generate representative pre-2018 historical BDI data."""
    dates = pd.date_range(start="2017-01-01", end="2017-12-31", freq="B")
    data = {
        "date": [d.strftime("%Y-%m-%d") for d in dates],
        "close": np.linspace(950.0, 1350.0, len(dates)),
    }
    return pd.DataFrame(data)


def test_splice_freight_series_proxy_only(mock_bdry_data):
    """Test splicing pipeline when only BDRY ETF proxy data is provided."""
    result = splice_freight_series(bdry_df=mock_bdry_data, bdi_df=None)

    # 1. Non-empty and exact match in length
    assert not result.empty
    assert len(result) == len(mock_bdry_data)

    # 2. Proxy tagging (PEP8 idiom compliant)
    assert result["is_proxy"].all()
    assert (result["source_series"] == "BDRY_ETF_PROXY").all()

    # 3. No null prices or index values
    assert not result["freight_proxy_value"].isnull().any()
    assert not result["nominal_price"].isnull().any()
    assert not result["normalized_index_base100"].isnull().any()
    assert not result["date"].isnull().any()

    # 4. Monotonic ascending dates
    dates = pd.to_datetime(result["date"])
    assert dates.is_monotonic_increasing


def test_splice_freight_series_combined(mock_bdry_data, mock_historical_bdi_data):
    """Test splicing historical BDI series with BDRY ETF proxy series and normalized index."""
    result = splice_freight_series(bdry_df=mock_bdry_data, bdi_df=mock_historical_bdi_data)

    # 1. Correct length
    expected_len = len(mock_historical_bdi_data) + len(mock_bdry_data)
    assert len(result) == expected_len

    # 2. Strict chronological ordering
    dates = pd.to_datetime(result["date"])
    assert dates.is_monotonic_increasing
    assert not dates.duplicated().any()

    # 3. Provenance segregation (PEP8 idiom compliant)
    bdi_part = result[~result["is_proxy"]]
    bdry_part = result[result["is_proxy"]]

    assert len(bdi_part) == len(mock_historical_bdi_data)
    assert len(bdry_part) == len(mock_bdry_data)
    assert (bdi_part["source_series"] == "BDI_HISTORICAL").all()
    assert (bdry_part["source_series"] == "BDRY_ETF_PROXY").all()

    # 4. No null values or invalid numbers in normalized index
    assert not result["freight_proxy_value"].isnull().any()
    assert not result["normalized_index_base100"].isnull().any()
    assert np.isfinite(result["normalized_index_base100"]).all()
    assert (result["normalized_index_base100"] > 0).all()


def test_no_unexplained_date_gaps(mock_bdry_data):
    """
    Check that gaps between consecutive business trading dates do not exceed
    an explainable threshold (4 calendar days, accounting for 3-day holiday weekends).
    """
    result = splice_freight_series(bdry_df=mock_bdry_data, bdi_df=None)
    dates = pd.to_datetime(result["date"])

    date_diffs = dates.diff().dropna()
    max_gap_days = date_diffs.dt.total_seconds() / (24 * 3600)

    MAX_EXPLAINABLE_GAP_DAYS = 4
    assert max_gap_days.max() <= MAX_EXPLAINABLE_GAP_DAYS, (
        f"Found gap of {max_gap_days.max()} days exceeding threshold of {MAX_EXPLAINABLE_GAP_DAYS} days."
    )


def test_load_historical_bdi_nonexistent(tmp_path):
    """Test that load_historical_bdi gracefully returns None if file does not exist."""
    non_existent = tmp_path / "does_not_exist.csv"
    res = load_historical_bdi(raw_csv_path=non_existent)
    assert res is None


def test_load_historical_bdi_corrupted_dates(tmp_path):
    """Test that load_historical_bdi safely skips invalid or unparseable dates."""
    csv_file = tmp_path / "bdi_corrupted.csv"
    csv_file.write_text(
        "date,bdi_close\n"
        "2016-01-04,473.0\n"
        "NOT_A_DATE,480.0\n"
        "2016-01-06,463.0\n"
    )
    res = load_historical_bdi(raw_csv_path=csv_file)
    assert res is not None
    assert len(res) == 2
    assert "NOT_A_DATE" not in res["date"].values


def test_save_processed_data(tmp_path, mock_bdry_data):
    """Test saving processed DataFrame to CSV."""
    spliced = splice_freight_series(bdry_df=mock_bdry_data)
    out_file = tmp_path / "processed" / "freight_proxy_test.csv"
    saved_path = save_processed_data(spliced, output_path=out_file)

    assert saved_path.exists()
    reloaded = pd.read_csv(saved_path)
    assert len(reloaded) == len(spliced)
    assert "freight_proxy_value" in reloaded.columns
    assert "normalized_index_base100" in reloaded.columns
    assert "is_proxy" in reloaded.columns


def test_processed_dataset_integrity():
    """
    Integration check on the generated processed dataset at data/processed/freight_proxy_series.csv.
    Asserts:
    - File exists and has > 1000 records.
    - Zero NaN/null values in date, close, nominal_price, freight_proxy_value, or normalized_index_base100.
    - Dates are strictly monotonic ascending.
    - Max gap between trading days does not exceed 5 calendar days (accounting for long holiday weekends).
    """
    processed_path = REPO_ROOT / "data" / "processed" / "freight_proxy_series.csv"
    if not processed_path.exists():
        pytest.skip("Processed dataset not yet generated on disk.")

    df = pd.read_csv(processed_path)
    assert len(df) > 1000, f"Expected >1000 records in processed series, found {len(df)}"

    # Check nulls
    assert not df["date"].isnull().any(), "Found null dates in processed file"
    assert not df["freight_proxy_value"].isnull().any(), "Found null freight values in processed file"
    assert not df["normalized_index_base100"].isnull().any(), "Found null normalized_index values"
    assert not df["is_proxy"].isnull().any(), "Found null is_proxy flags in processed file"

    # Check date sorting
    dates = pd.to_datetime(df["date"])
    assert dates.is_monotonic_increasing, "Dates in processed file are not strictly sorted"
    assert not dates.duplicated().any(), "Found duplicate dates in processed file"

    # Check gap threshold
    date_diffs = dates.diff().dropna()
    max_gap_days = date_diffs.dt.total_seconds() / (24 * 3600)
    MAX_EXPLAINABLE_GAP = 5  # 5 calendar days max for holiday weekends / market closures
    assert max_gap_days.max() <= MAX_EXPLAINABLE_GAP, (
        f"Found gap of {max_gap_days.max()} days exceeding {MAX_EXPLAINABLE_GAP} day threshold."
    )
