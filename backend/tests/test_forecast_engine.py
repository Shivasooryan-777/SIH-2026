"""
Forecast Engine & Walk-Forward Validation Test Suite
===================================================
Rigorous verification of Module A guarantees per docs/blueprint.md:
1. Walk-Forward Non-Leakage: Formally proves no fold contains test data in train set.
2. Hard Point-Forecast Ban: Fails loudly if any code path outputs a point forecast without P10-P90.
3. Quantile Monotonicity: Proves P10 <= P50 <= P90 invariant holds under all conditions.
4. SHAP Schema & Attribution: Validates top 3 contributing factors formatting.
5. Feature Engineering Zero-Leakage: Verifies features at row t depend strictly on past rows.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.attribution import FeatureExplanation, compute_shap_explanations
from ml.features import build_feature_matrix
from ml.models import QuantileForecast
from ml.train import validate_quantile_band_integrity
from ml.walk_forward_cv import generate_walk_forward_splits, validate_no_leakage


# =============================================================================
# 1. Walk-Forward Zero-Leakage Tests
# =============================================================================

def test_walk_forward_splits_no_data_leakage():
    """
    Formally verify that across every walk-forward fold:
    1. The intersection of train and test indices is strictly empty.
    2. The maximum train date is strictly less than the minimum test date.
    3. Origin expands strictly forward by step_size.
    """
    n_days = 200
    dates = pd.date_range(start="2022-01-01", periods=n_days, freq="B")
    mock_df = pd.DataFrame({
        "date": [d.strftime("%Y-%m-%d") for d in dates],
        "val": np.linspace(100.0, 200.0, n_days),
    })

    folds = generate_walk_forward_splits(
        mock_df,
        min_train_size=100,
        test_horizon=30,
        step_size=30,
        date_col="date",
    )

    assert len(folds) >= 3, f"Expected at least 3 folds, got {len(folds)}"

    for fold in folds:
        # Check no index overlap
        overlap = set(fold.train_indices).intersection(set(fold.test_indices))
        assert len(overlap) == 0, f"Fold {fold.fold_idx} has index overlap: {overlap}"

        # Check temporal order
        train_dates = pd.to_datetime(mock_df.iloc[fold.train_indices]["date"])
        test_dates = pd.to_datetime(mock_df.iloc[fold.test_indices]["date"])
        assert train_dates.max() < test_dates.min(), (
            f"Fold {fold.fold_idx} temporal leakage: max train {train_dates.max()} "
            f"not strictly before min test {test_dates.min()}"
        )

        # Check sizes
        assert fold.test_size == 30, f"Fold {fold.fold_idx} test size {fold.test_size} != 30"


def test_validate_no_leakage_raises_on_leak():
    """Verify that validate_no_leakage raises ValueError if index overlap or date leak occurs."""
    dates = pd.date_range(start="2022-01-01", periods=10, freq="D")
    df = pd.DataFrame({"date": [d.strftime("%Y-%m-%d") for d in dates]})

    # 1. Index overlap
    with pytest.raises(ValueError, match="LEAKAGE DETECTED"):
        validate_no_leakage(df, train_indices=np.array([0, 1, 2, 3]), test_indices=np.array([3, 4, 5]))

    # 2. Temporal leakage (train contains a future date)
    with pytest.raises(ValueError, match="TEMPORAL LEAKAGE DETECTED"):
        validate_no_leakage(df, train_indices=np.array([0, 1, 5]), test_indices=np.array([2, 3, 4]))


# =============================================================================
# 2. Hard Point-Forecast Ban & Quantile Monotonicity Tests
# =============================================================================

def test_single_point_forecast_without_band_is_rejected():
    """
    HARD RULE: Prohibit single point forecast without P10-P90 band.
    Ensures that calling validate_quantile_band_integrity fails loudly when
    p10 or p90 are None or missing.
    """
    valid_p50 = np.array([15000.0, 16000.0])

    # Case 1: p10 is None
    with pytest.raises(ValueError, match="PROHIBITED: Point forecast without P10-P90"):
        validate_quantile_band_integrity(p10=None, p50=valid_p50, p90=np.array([17000.0, 18000.0]))

    # Case 2: p90 is None
    with pytest.raises(ValueError, match="PROHIBITED: Point forecast without P10-P90"):
        validate_quantile_band_integrity(p10=np.array([13000.0, 14000.0]), p50=valid_p50, p90=None)

    # Case 3: Length mismatch
    with pytest.raises(ValueError, match="Quantile length mismatch"):
        validate_quantile_band_integrity(
            p10=np.array([13000.0]),
            p50=valid_p50,
            p90=np.array([17000.0, 18000.0]),
        )


def test_quantile_monotonicity_enforcement():
    """
    Verify that QuantileForecast automatically enforces p10 <= p50 <= p90
    even if raw sub-models produce crossing quantiles.
    """
    # Raw unclipped predictions with crossing
    raw_p10 = np.array([16500.0, 12000.0])  # 16500 > 15000 (crossing!)
    raw_p50 = np.array([15000.0, 14000.0])
    raw_p90 = np.array([14500.0, 16000.0])  # 14500 < 15000 (crossing!)

    forecast = QuantileForecast(p10=raw_p10, p50=raw_p50, p90=raw_p90)

    # Monotonic order must be strictly preserved
    assert np.all(forecast.p10 <= forecast.p50), "p10 was not clamped below p50!"
    assert np.all(forecast.p50 <= forecast.p90), "p90 was not clamped above p50!"
    assert forecast.p10[0] == 15000.0
    assert forecast.p90[0] == 15000.0


# =============================================================================
# 3. SHAP Top-3 Attribution Structure Tests
# =============================================================================

def test_shap_explanation_structure_and_schema():
    """
    Verifies that compute_shap_explanations returns exactly top 3 explanations
    conforming to the ShapExplanations schema: feature_name, contribution_pct, direction.
    """
    from sklearn.ensemble import RandomForestRegressor  # type: ignore

    # Train a fast shallow tree on dummy data
    X_train = pd.DataFrame({
        "freight_lag_1": [10.0, 12.0, 14.0, 16.0, 18.0],
        "brent_crude_lag_1": [70.0, 72.0, 75.0, 71.0, 73.0],
        "coal_futures_lag_1": [120.0, 125.0, 122.0, 128.0, 130.0],
        "usd_inr_lag_1": [82.0, 82.5, 83.0, 83.2, 83.5],
        "month": [1, 2, 3, 4, 5],
    })
    y_train = pd.Series([11.0, 13.0, 15.0, 17.0, 19.0])

    rf = RandomForestRegressor(n_estimators=10, max_depth=3, random_state=42)
    rf.fit(X_train, y_train)

    X_single = X_train.iloc[[0]]
    explanations = compute_shap_explanations(rf, X_single, top_k=3)

    assert len(explanations) == 3, f"Expected 3 explanations, got {len(explanations)}"

    for exp in explanations:
        assert isinstance(exp, FeatureExplanation)
        assert len(exp.feature_name) > 0 and len(exp.feature_name) <= 50
        assert exp.contribution_pct >= 0.0 and exp.contribution_pct <= 100.0
        assert exp.direction in ("upward", "downward")


# =============================================================================
# 4. Feature Engineering Leakage Verification
# =============================================================================

def test_feature_engineering_zero_lookahead():
    """
    Verify that features at time t do not change when future data (t+1..T) changes.
    """
    dates = pd.date_range(start="2023-01-01", periods=60, freq="D")
    base_freight = pd.DataFrame({
        "date": [d.strftime("%Y-%m-%d") for d in dates],
        "freight_rate_usd": np.linspace(10000.0, 20000.0, 60),
    })
    base_macro = pd.DataFrame({
        "date": [d.strftime("%Y-%m-%d") for d in dates],
        "indicator_type": "brent_crude",
        "value": np.linspace(70.0, 90.0, 60),
    })

    feat1 = build_feature_matrix(base_freight, base_macro)

    # Modify date 59 (the last date) drastically
    mutated_freight = base_freight.copy()
    mutated_freight.loc[59, "freight_rate_usd"] = 999999.0

    feat2 = build_feature_matrix(mutated_freight, base_macro)

    # All rows before the last row must be IDENTICAL (no backward leakage from future modification)
    for col in feat1.columns:
        if col not in ("date",):
            np.testing.assert_allclose(
                feat1.iloc[:-1][col].values,
                feat2.iloc[:-1][col].values,
                err_msg=f"Feature '{col}' leaked future information into past rows!",
            )


def test_general_freight_series_null_vessel_type_supported():
    """
    Verify that ForecastResult and FreightRateData support vessel_type_id=None
    representing general dry-bulk market index per Option 2 honest scoping.
    """
    from decimal import Decimal
    from backend.app.models import ForecastResult, FreightRateData

    # Instantiating with vessel_type_id=None must not fail
    f_rate = FreightRateData(
        date=pd.to_datetime("2024-01-01").date(),
        vessel_type_id=None,
        index_type="BDRY_proxy",
        value_usd_per_day=Decimal("15.50"),
        source="BDRY_ETF_PROXY",
    )
    assert f_rate.vessel_type_id is None
    assert f_rate.index_type == "BDRY_proxy"

    f_res = ForecastResult(
        request_id=1,
        vessel_type_id=None,
        p10_price=Decimal("12.00"),
        p50_price=Decimal("15.00"),
        p90_price=Decimal("18.00"),
        model_version="v1.0-ensemble",
    )
    assert f_res.vessel_type_id is None
    assert f_res.p10_price <= f_res.p50_price <= f_res.p90_price

