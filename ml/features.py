"""
Feature Engineering Pipeline for Module A (Forecast Engine)
===========================================================
Extracts daily time series from Neon Postgres (FreightRateData and MacroIndicators),
aligns series on trading dates, and constructs zero-leakage predictive features:
- Lag features: t-1, t-7, t-30
- Rolling averages: MA7, MA30 (strictly lagged by 1 step)
- Momentum and Rate-of-Change (ROC): 7-day and 30-day
- Macro leading indicators: Brent crude, USD/INR, coal futures proxy, iron ore proxy
- Calendar features: month of year, day of week

STRICT LEAKAGE INVARIANT:
All features at observation row t depend strictly on data available at or before t-1.
"""

import logging
import sys
from pathlib import Path
from typing import List, Optional, Tuple, cast

import numpy as np
import pandas as pd

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.database import SessionLocal
from backend.app.models import FreightRateData, MacroIndicator, VesselType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ml.features")


def load_raw_data_from_db() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Fetch the single real general dry-bulk freight series (vessel_type_id IS NULL)
    and macro indicators from Neon Postgres.

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: (freight_df, macro_df)
    """
    db = SessionLocal()
    try:
        # Query single honest general dry-bulk freight series (vessel_type_id IS NULL)
        freight_rows = (
            db.query(FreightRateData.date, FreightRateData.value_usd_per_day)
            .filter(FreightRateData.vessel_type_id.is_(None))
            .order_by(FreightRateData.date.asc())
            .all()
        )

        freight_records = [
            {
                "date": str(r[0]),
                "freight_rate_usd": float(r[1]),
            }
            for r in freight_rows
        ]
        freight_df = pd.DataFrame(freight_records)

        # Query MacroIndicators
        macro_rows = (
            db.query(MacroIndicator.date, MacroIndicator.indicator_type, MacroIndicator.value)
            .order_by(MacroIndicator.date.asc())
            .all()
        )

        macro_records = [
            {
                "date": str(r[0]),
                "indicator_type": str(r[1]),
                "value": float(r[2]),
            }
            for r in macro_rows
        ]
        macro_df = pd.DataFrame(macro_records)

        logger.info(
            "Loaded from Neon: %d general freight records (vessel_type_id=NULL), %d macro records",
            len(freight_df),
            len(macro_df),
        )
        return freight_df, macro_df

    except Exception as exc:
        logger.warning("Failed to query Neon Postgres (%s). Falling back to local processed CSVs.", exc)
        return load_raw_data_from_csv()
    finally:
        db.close()


def load_raw_data_from_csv(
    freight_csv: Optional[Path] = None,
    macro_csv: Optional[Path] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Fallback data loader reading unscaled raw BDRY series directly from local processed CSVs.
    Zero synthetic multipliers or artificial scaling.
    """
    freight_path = freight_csv or (REPO_ROOT / "data" / "processed" / "freight_proxy_series.csv")
    macro_path = macro_csv or (REPO_ROOT / "data" / "processed" / "macro_indicators_series.csv")

    f_df = pd.read_csv(freight_path)
    # Raw BDRY ETF proxy closing price in USD/share (no multipliers)
    raw_price = f_df["freight_proxy_value"] if "freight_proxy_value" in f_df else f_df["close"]
    freight_df = pd.DataFrame({
        "date": f_df["date"].astype(str),
        "freight_rate_usd": raw_price.astype(float),
    })

    m_df = pd.read_csv(macro_path)
    macro_df = pd.DataFrame({
        "date": m_df["date"].astype(str),
        "indicator_type": m_df["indicator_type"].astype(str),
        "value": m_df["value"].astype(float),
    })
    return freight_df, macro_df


def build_feature_matrix(
    freight_df: pd.DataFrame,
    macro_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Transform raw time series into feature matrix with zero-leakage lag and rolling features.

    Returns:
        pd.DataFrame: Fully engineered dataset with target 'target_freight_usd' and all features.
    """
    if freight_df.empty:
        raise ValueError("Freight DataFrame is empty!")

    freight_df = freight_df.copy()
    freight_df["date"] = pd.to_datetime(freight_df["date"])
    freight_df = freight_df.sort_values("date").drop_duplicates(subset=["date"]).reset_index(drop=True)

    # Pivot macro indicators to wide format: columns for each indicator
    if not macro_df.empty:
        macro_df = macro_df.copy()
        macro_df["date"] = pd.to_datetime(macro_df["date"])
        macro_pivot = macro_df.pivot_table(index="date", columns="indicator_type", values="value", aggfunc="mean")
        macro_pivot = macro_pivot.ffill().bfill().reset_index()
    else:
        macro_pivot = pd.DataFrame({"date": freight_df["date"]})

    # Merge on date index
    merged = pd.merge(freight_df, macro_pivot, on="date", how="left")
    merged = merged.sort_values("date").reset_index(drop=True)

    # Forward fill any intermittent weekend/holiday gaps in macro indicators
    merged = merged.ffill().bfill()

    features = pd.DataFrame({"date": merged["date"].dt.strftime("%Y-%m-%d")})
    # Target is the current day's freight rate
    features["target_freight_usd"] = merged["freight_rate_usd"].values

    rate_series = merged["freight_rate_usd"]

    # 1. Freight Rate Lags (t-1, t-7, t-30)
    features["freight_lag_1"] = rate_series.shift(1)
    features["freight_lag_7"] = rate_series.shift(7)
    features["freight_lag_30"] = rate_series.shift(30)

    # 2. Freight Rolling Averages (MA7, MA30 strictly lagged by 1 day)
    features["freight_ma_7"] = rate_series.shift(1).rolling(window=7, min_periods=7).mean()
    features["freight_ma_30"] = rate_series.shift(1).rolling(window=30, min_periods=30).mean()

    # 3. Freight Rate-of-Change / Momentum
    # 7-day ROC: (P_{t-1} - P_{t-8}) / P_{t-8}
    features["freight_roc_7"] = (rate_series.shift(1) - rate_series.shift(8)) / rate_series.shift(8)
    # 30-day ROC: (P_{t-1} - P_{t-31}) / P_{t-31}
    features["freight_roc_30"] = (rate_series.shift(1) - rate_series.shift(31)) / rate_series.shift(31)
    # 7-day Momentum
    features["freight_momentum_7"] = rate_series.shift(1) - rate_series.shift(8)

    # 4. Macro Indicator Features (Brent, USD/INR, Coal, Iron Ore)
    indicator_cols = [c for c in merged.columns if c not in ["date", "freight_rate_usd"]]
    for col in indicator_cols:
        series = merged[col]
        features[f"{col}_lag_1"] = series.shift(1)
        features[f"{col}_lag_7"] = series.shift(7)
        features[f"{col}_lag_30"] = series.shift(30)
        features[f"{col}_ma_7"] = series.shift(1).rolling(window=7, min_periods=7).mean()
        features[f"{col}_ma_30"] = series.shift(1).rolling(window=30, min_periods=30).mean()
        features[f"{col}_roc_7"] = (series.shift(1) - series.shift(8)) / (series.shift(8).abs() + 1e-6)

    # 5. Calendar Seasonality Features
    features["month"] = merged["date"].dt.month
    features["day_of_week"] = merged["date"].dt.dayofweek

    # Drop the first 31 rows containing NaNs from the 30-day lookback window
    clean_features = features.dropna().reset_index(drop=True)
    logger.info(
        "Constructed feature matrix: %d rows x %d columns (from %d raw dates)",
        len(clean_features),
        clean_features.shape[1],
        len(freight_df),
    )
    return clean_features


def prepare_features(
    from_db: bool = True,
) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    """
    Convenience orchestrator returning (X, y, feature_names) for the single honest general dry-bulk series.
    """
    if from_db:
        f_df, m_df = load_raw_data_from_db()
    else:
        f_df, m_df = load_raw_data_from_csv()

    feat_df = build_feature_matrix(f_df, m_df)
    feature_cols: List[str] = [str(c) for c in feat_df.columns if str(c) not in ["date", "target_freight_usd"]]

    X = feat_df[feature_cols].copy()
    y = cast(pd.Series, feat_df["target_freight_usd"].copy())
    return feat_df, y, feature_cols
