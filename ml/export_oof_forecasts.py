"""
Multi-Horizon Out-of-Fold Forecast Exporter
===========================================
Generates strictly forward-looking quantile forecasts (P10/P50/P90) specifically issued
FROM each historical fixture origin date t0, covering candidate decision horizons
N in [7, 14, 21, 28] days.

ZERO-LEAKAGE METHODOLOGY:
- For any origin date t0, the quantile model is trained EXCLUSIVELY on data available
  at or before t0 (history <= t0).
- Forward multi-step predictions are generated using recursive autoregressive roll-forward,
  where model predictions feed into subsequent lag features rather than actual future prices.
- At no point does the model observe or condition on any market prices after t0.

DISCLOSED MODELING LIMITATIONS:
1. Extrapolation Boundary: Tree-based models (XGBoost, LightGBM) partition the feature
   space and cannot extrapolate beyond the minimum and maximum target price values
   observed in the training sample up to t0.
2. Recursive Multi-Step Dynamics: In recursive autoregressive forecasting across 7, 14,
   21, and 28-day forward horizons, compounding predictions can dampen volatility or
   occasionally produce non-monotonic trajectory variations at longer horizons.
   This is a documented structural characteristic of tree ensembles applied to multi-step
   forecasting, disclosed proactively per blueprint standards.

LOCAL CACHE ONLY:
- The generated output is written strictly to local disk at data/processed/oof_forecasts_series.csv.
- It is NEVER written to the live Neon Postgres database.

HARDWARE SAFETY:
- Maximum execution time budget: 60.0 seconds.
- Minimum available system RAM: 500 MB.
- CPU-only execution (device='cpu', n_jobs=2).
"""

import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import psutil  # type: ignore

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.features import build_feature_matrix, load_raw_data_from_csv
from ml.models import EnsembleQuantileModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ml.export_oof")

# HARDWARE SAFETY BUDGET
MAX_TIME_BUDGET_SECONDS = 60.0
MIN_AVAILABLE_RAM_MB = 500.0

# 25 REPRESENTATIVE FIXTURE ORIGIN DATES (2020–2024)
FIXTURE_ORIGIN_DATES = [
    "2020-04-15",
    "2020-06-16",
    "2020-08-18",
    "2020-10-20",
    "2020-12-15",
    "2021-02-16",
    "2021-04-20",
    "2021-06-15",
    "2021-08-17",
    "2021-10-19",
    "2021-12-14",
    "2022-02-15",
    "2022-04-19",
    "2022-06-21",
    "2022-08-16",
    "2022-10-18",
    "2022-12-20",
    "2023-02-21",
    "2023-04-18",
    "2023-06-20",
    "2023-08-15",
    "2023-10-17",
    "2023-12-19",
    "2024-02-20",
    "2024-04-16",
]

CANDIDATE_HORIZONS_DAYS = [7, 14, 21, 28]


def verify_hardware_safety():
    """Verify available system RAM before training."""
    available_ram_mb = psutil.virtual_memory().available / (1024.0 * 1024.0)
    logger.info("Hardware Safety Check: Available RAM: %.1f MB", available_ram_mb)
    if available_ram_mb < MIN_AVAILABLE_RAM_MB:
        raise MemoryError(
            f"ABORT: System RAM ({available_ram_mb:.1f} MB) is below safe minimum ({MIN_AVAILABLE_RAM_MB} MB)."
        )


def export_multi_horizon_forecasts(output_path: Optional[Path] = None) -> Tuple[pd.DataFrame, float]:
    """
    Train strictly on data <= t0 for each fixture origin and generate multi-horizon forecasts.
    Returns (DataFrame of forecasts, measured execution time in seconds).
    """
    start_time = time.monotonic()
    verify_hardware_safety()

    dest_csv = output_path or (REPO_ROOT / "data" / "processed" / "oof_forecasts_series.csv")
    dest_csv.parent.mkdir(parents=True, exist_ok=True)

    f_df, m_df = load_raw_data_from_csv()
    feat_df = build_feature_matrix(f_df, m_df)
    feature_cols = [c for c in feat_df.columns if c not in ["date", "target_freight_usd"]]

    all_dates = feat_df["date"].tolist()
    date_to_idx = {d: i for i, d in enumerate(all_dates)}

    records: List[Dict] = []
    logger.info("Starting multi-horizon out-of-fold export across %d fixture origins...", len(FIXTURE_ORIGIN_DATES))

    for idx, origin_date in enumerate(FIXTURE_ORIGIN_DATES, start=1):
        elapsed = time.monotonic() - start_time
        if elapsed > MAX_TIME_BUDGET_SECONDS:
            raise TimeoutError(
                f"HARD TIME BUDGET EXCEEDED: Elapsed {elapsed:.2f}s exceeds limit of {MAX_TIME_BUDGET_SECONDS}s at origin {origin_date}!"
            )

        if origin_date not in date_to_idx:
            # Find closest previous trading date
            prev_dates = [d for d in all_dates if d <= origin_date]
            if not prev_dates:
                raise ValueError(f"No trading dates available on or before {origin_date}")
            actual_origin = prev_dates[-1]
            logger.warning("Origin %s not a trading date; snapped to prior trading date %s", origin_date, actual_origin)
        else:
            actual_origin = origin_date

        origin_idx = date_to_idx[actual_origin]
        # Strict temporal non-leakage: training set is strictly <= origin_idx
        train_df = feat_df.iloc[: origin_idx + 1].copy()
        X_train = train_df[feature_cols]
        y_train = train_df["target_freight_usd"]
        dates_train = train_df["date"]

        # Current price at t0
        f_now = float(y_train.iloc[-1])

        # Fit model on history up to t0
        ensemble = EnsembleQuantileModel()
        ensemble.fit(X_train, y_train, dates_train)

        # Autoregressive multi-horizon roll-forward
        # We roll forward up to 28 days
        curr_feat_row = X_train.iloc[[-1]].copy()
        pred_history = list(y_train.iloc[-35:].values)

        for h in range(1, max(CANDIDATE_HORIZONS_DAYS) + 1):
            # Target calendar date
            curr_date_dt = datetime.strptime(actual_origin, "%Y-%m-%d") + timedelta(days=h)
            curr_date_str = curr_date_dt.strftime("%Y-%m-%d")

            # Update lag features in curr_feat_row using past predictions
            curr_feat_row["freight_lag_1"] = pred_history[-1]
            curr_feat_row["freight_lag_7"] = pred_history[-7] if len(pred_history) >= 7 else pred_history[0]
            curr_feat_row["freight_lag_30"] = pred_history[-30] if len(pred_history) >= 30 else pred_history[0]
            curr_feat_row["freight_ma_7"] = np.mean(pred_history[-7:])
            curr_feat_row["freight_ma_30"] = np.mean(pred_history[-30:])
            curr_feat_row["month"] = curr_date_dt.month
            curr_feat_row["day_of_week"] = curr_date_dt.weekday()

            # Predict 1-step quantiles from current rolling state
            preds = ensemble.predict(curr_feat_row, pd.Series([curr_date_str]), calibration_multiplier=1.2)
            step_p10 = float(preds.p10[0])
            step_p50 = float(preds.p50[0])
            step_p90 = float(preds.p90[0])

            # Push p50 into prediction history for autoregressive roll
            pred_history.append(step_p50)

            # Record candidate horizons
            if h in CANDIDATE_HORIZONS_DAYS:
                records.append({
                    "origin_date": actual_origin,
                    "horizon_days": h,
                    "target_date": curr_date_str,
                    "f_now": round(f_now, 2),
                    "p10_price": round(step_p10, 2),
                    "p50_price": round(step_p50, 2),
                    "p90_price": round(step_p90, 2),
                    "spread": round(step_p90 - step_p10, 2),
                })

        logger.info(
            "[%d/%d] Origin %s: f_now=$%.2f | +14d: p50=$%.2f (spread=$%.2f)",
            idx,
            len(FIXTURE_ORIGIN_DATES),
            actual_origin,
            f_now,
            records[-3]["p50_price"],  # +14d is 2nd of 4 records
            records[-3]["spread"],
        )

    oof_df = pd.DataFrame(records)
    oof_df.to_csv(dest_csv, index=False)

    total_time = time.monotonic() - start_time
    logger.info("Successfully exported %d multi-horizon forecasts to local CSV: %s", len(oof_df), dest_csv)
    logger.info("Total execution time: %.2f seconds (Budget: %.0fs)", total_time, MAX_TIME_BUDGET_SECONDS)

    return oof_df, total_time


if __name__ == "__main__":
    df, elapsed = export_multi_horizon_forecasts()
    print(f"SUCCESS: Exported {len(df)} rows in {elapsed:.2f} seconds.")
