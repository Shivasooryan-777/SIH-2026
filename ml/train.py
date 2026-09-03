"""
Walk-Forward Model Training & Evaluation Harness
================================================
Orchestrates genuine rolling-origin cross-validation, out-of-fold performance
evaluation, hardware safety guards, and persistence to Neon Postgres.

STRICT PROTOCOLS (docs/blueprint.md Module A):
1. Walk-Forward CV ONLY: [T0..T1] -> [T1..T1+30 days], expanding forward.
2. Out-of-fold accuracy ONLY (MAE, RMSE, MAPE, P10-P90 coverage).
3. Monotonic P10 <= P50 <= P90 quantile forecasts.
4. Hard rejection of point forecasts without P10-P90 uncertainty band.
5. SHAP feature attribution (top 3 factors) persisted to ShapExplanations.
6. Hardware safety: RAM pre-check, CPU-only, hard 180-second time budget.
"""

import logging
import sys
import time
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

import numpy as np
import pandas as pd
import psutil  # type: ignore

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.database import SessionLocal
from backend.app.models import (
    CargoRequest,
    ForecastResult,
    Port,
    ShapExplanation,
    VesselType,
)
from ml.attribution import compute_shap_explanations
from ml.features import prepare_features
from ml.models import EnsembleQuantileModel, LightGBMQuantileModel, XGBoostQuantileModel
from ml.walk_forward_cv import generate_walk_forward_splits

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ml.train")

# HARDWARE SAFETY CONSTANTS
MAX_TIME_BUDGET_SECONDS = 180.0  # 3 minutes maximum total training time
MIN_AVAILABLE_RAM_MB = 500.0     # Abort if available RAM is below 500 MB


def verify_hardware_safety(df: pd.DataFrame) -> None:
    """
    Check memory footprint and system available RAM before starting training.
    """
    mem_bytes = df.memory_usage(deep=True).sum()
    mem_kb = mem_bytes / 1024.0
    mem_mb = mem_kb / 1024.0

    available_ram_mb = psutil.virtual_memory().available / (1024.0 * 1024.0)

    logger.info("=== HARDWARE SAFETY PRE-FLIGHT CHECK ===")
    logger.info("Dataset shape: %d rows x %d cols", df.shape[0], df.shape[1])
    logger.info("In-memory dataset footprint: %.2f KB (%.3f MB)", mem_kb, mem_mb)
    logger.info("Available system RAM: %.1f MB (%.2f GB)", available_ram_mb, available_ram_mb / 1024.0)
    logger.info("Hardware target: Laptop CPU (device='cpu', n_jobs=2)")
    logger.info("Execution time budget: %.0f seconds", MAX_TIME_BUDGET_SECONDS)

    if available_ram_mb < MIN_AVAILABLE_RAM_MB:
        raise MemoryError(
            f"ABORT: Available system RAM ({available_ram_mb:.1f} MB) is below safe threshold "
            f"({MIN_AVAILABLE_RAM_MB} MB). Halting to prevent machine lockup."
        )


def validate_quantile_band_integrity(p10: Optional[np.ndarray], p50: np.ndarray, p90: Optional[np.ndarray]) -> None:
    """
    Strict project rule: Never output or persist a single point forecast without P10-P90 band.
    """
    if p10 is None or p90 is None:
        raise ValueError("PROHIBITED: Point forecast without P10-P90 uncertainty band is strictly forbidden!")
    if len(p10) != len(p50) or len(p50) != len(p90):
        raise ValueError("Quantile length mismatch across P10, P50, and P90 arrays!")
    if np.any(np.isnan(p10)) or np.any(np.isnan(p50)) or np.any(np.isnan(p90)):
        raise ValueError("NaN values detected in quantile predictions!")
    if np.any(p10 > p50) or np.any(p50 > p90):
        raise ValueError("Quantile monotonicity violation: p10 <= p50 <= p90 invariant broken!")


def get_or_create_benchmark_request(db) -> int:
    """
    Retrieve or create a baseline CargoRequest for associating out-of-fold validation forecasts.
    """
    req = db.query(CargoRequest).filter(CargoRequest.cargo_type == "coking_coal_benchmark").first()
    if req:
        return cast(int, req.request_id)

    origin = db.query(Port).filter(Port.port_role == "origin").first()
    dest = db.query(Port).filter(Port.port_role == "destination").first()

    origin_id = origin.port_id if origin else 1
    dest_id = dest.port_id if dest else 2

    new_req = CargoRequest(
        cargo_type="coking_coal_benchmark",
        cargo_volume_tons=75000,
        origin_port_id=origin_id,
        destination_port_id=dest_id,
        desired_timeframe_days=30,
        desired_contract_pref="spot",
    )
    db.add(new_req)
    db.commit()
    db.refresh(new_req)
    return cast(int, new_req.request_id)


def run_walk_forward_training(
    test_horizon: int = 30,
    step_size: int = 30,
    min_train_size: int = 500,
    save_to_db: bool = True,
) -> Dict[str, float]:
    """
    Execute rolling-origin cross-validation on the single honest general dry-bulk freight series,
    apply conformal calibration to guarantee target coverage, calculate out-of-fold metrics,
    and persist results with vessel_type_id=NULL into Neon Postgres.
    """
    start_time = time.monotonic()

    feat_df, y_series, feature_cols = prepare_features(from_db=True)
    verify_hardware_safety(feat_df)

    X_data = feat_df[feature_cols]
    y_data = y_series
    dates_data = feat_df["date"]

    folds = generate_walk_forward_splits(
        feat_df,
        min_train_size=min_train_size,
        test_horizon=test_horizon,
        step_size=step_size,
        date_col="date",
    )
    logger.info("Generated %d rolling-origin walk-forward folds.", len(folds))

    oof_actuals: List[float] = []
    oof_p10: List[float] = []
    oof_p50: List[float] = []
    oof_p90: List[float] = []
    oof_dates: List[str] = []
    oof_features: List[pd.DataFrame] = []
    oof_fitted_trees: List[Any] = []
    oof_past_scores: List[float] = []

    for fold in folds:
        elapsed = time.monotonic() - start_time
        if elapsed > MAX_TIME_BUDGET_SECONDS:
            logger.warning(
                "TIME BUDGET EXCEEDED: Elapsed %.1fs exceeds %.0fs limit. Terminating walk-forward loop at fold %d/%d.",
                elapsed,
                MAX_TIME_BUDGET_SECONDS,
                fold.fold_idx,
                len(folds),
            )
            break

        X_train = X_data.iloc[fold.train_indices]
        y_train = y_data.iloc[fold.train_indices]
        dates_train = dates_data.iloc[fold.train_indices]

        X_test = X_data.iloc[fold.test_indices]
        y_test = y_data.iloc[fold.test_indices]
        dates_test = dates_data.iloc[fold.test_indices]

        logger.info(
            "Fold %d: Train [%s..%s] (%d rows) -> Test [%s..%s] (%d rows)",
            fold.fold_idx + 1,
            fold.train_start_date,
            fold.train_end_date,
            fold.train_size,
            fold.test_start_date,
            fold.test_end_date,
            fold.test_size,
        )

        ensemble = EnsembleQuantileModel()
        ensemble.fit(X_train, y_train, dates_train)

        # Rolling out-of-fold conformal calibration (calibrates on genuine past out-of-sample residuals, zero leakage)
        if len(oof_past_scores) >= 60:
            calib_mult = float(np.percentile(oof_past_scores, 80))
            calib_mult = float(np.clip(calib_mult, 0.8, 2.0))
        else:
            calib_mult = 1.25  # Prior scaling factor for early warmup folds

        preds = ensemble.predict(X_test, dates_test, calibration_multiplier=calib_mult)

        # Enforce band integrity
        validate_quantile_band_integrity(preds.p10, preds.p50, preds.p90)

        # Record genuine out-of-sample non-conformity scores from raw test predictions into pool for FUTURE folds
        raw_test = ensemble.predict(X_test, dates_test, calibration_multiplier=1.0)
        y_test_vals = y_test.values
        lower_d = np.maximum(raw_test.p50 - raw_test.p10, 1e-4)
        upper_d = np.maximum(raw_test.p90 - raw_test.p50, 1e-4)
        test_scores = np.maximum(
            (raw_test.p50 - y_test_vals) / lower_d,
            (y_test_vals - raw_test.p50) / upper_d,
        )
        oof_past_scores.extend(test_scores.tolist())

        oof_actuals.extend(y_test.values.tolist())
        oof_p10.extend(preds.p10.tolist())
        oof_p50.extend(preds.p50.tolist())
        oof_p90.extend(preds.p90.tolist())
        oof_dates.extend(dates_test.values.tolist())

        # Save test feature rows and the trained median tree model for SHAP attributions
        median_lgb_tree = ensemble.lgbm.models[0.50]
        for i in range(len(X_test)):
            oof_features.append(X_test.iloc[[i]])
            oof_fitted_trees.append(median_lgb_tree)

    # Convert to numpy arrays for strictly out-of-fold metrics
    actuals = np.array(oof_actuals)
    p10_arr = np.array(oof_p10)
    p50_arr = np.array(oof_p50)
    p90_arr = np.array(oof_p90)

    # Compute Out-of-Fold Performance Metrics (NEVER IN-SAMPLE)
    mae = float(np.mean(np.abs(actuals - p50_arr)))
    rmse = float(np.sqrt(np.mean((actuals - p50_arr) ** 2)))
    mape = float(np.mean(np.abs((actuals - p50_arr) / actuals)) * 100.0)

    # P10-P90 Coverage Ratio (% of actuals falling within predicted quantile band)
    coverage = float(np.mean((actuals >= p10_arr) & (actuals <= p90_arr)) * 100.0)

    total_time = time.monotonic() - start_time
    logger.info("=== OUT-OF-FOLD WALK-FORWARD VALIDATION RESULTS ===")
    logger.info("Total out-of-fold test samples: %d", len(actuals))
    logger.info("Out-of-Fold MAE:        $%.2f (BDRY index / share)", mae)
    logger.info("Out-of-Fold RMSE:       $%.2f", rmse)
    logger.info("Out-of-Fold MAPE:       %.2f %%", mape)
    logger.info("P10-P90 Coverage Ratio: %.2f %% (Target nominal: 80%%)", coverage)
    logger.info("Total execution time:   %.2f seconds", total_time)

    metrics = {
        "out_of_fold_mae": mae,
        "out_of_fold_rmse": rmse,
        "out_of_fold_mape": mape,
        "p10_p90_coverage_pct": coverage,
        "total_test_samples": len(actuals),
        "execution_time_seconds": total_time,
    }

    # Store results in Neon Postgres if requested
    if save_to_db and len(actuals) > 0:
        db = SessionLocal()
        try:
            # Assertion-gated purge of previous run's ForecastResults and ShapExplanations
            pre_f_count = db.query(ForecastResult).count()
            pre_s_count = db.query(ShapExplanation).count()
            if pre_f_count > 0:
                if pre_f_count != 30:
                    raise AssertionError(
                        f"Pre-delete assertion failed! Expected 30 ForecastResults, found {pre_f_count}"
                    )
                if pre_s_count != 90:
                    raise AssertionError(
                        f"Pre-delete assertion failed! Expected 90 ShapExplanations, found {pre_s_count}"
                    )

                del_s = db.query(ShapExplanation).delete(synchronize_session=False)
                del_f = db.query(ForecastResult).delete(synchronize_session=False)
                db.commit()

                if del_s != 90:
                    raise AssertionError(
                        f"Post-delete assertion failed! Expected 90 deleted ShapExplanations, got {del_s}"
                    )
                if del_f != 30:
                    raise AssertionError(
                        f"Post-delete assertion failed! Expected 30 deleted ForecastResults, got {del_f}"
                    )
                logger.info("Assertion-gated cleanup succeeded: deleted %d shap_explanations, %d forecast_results.", del_s, del_f)

            benchmark_req_id = get_or_create_benchmark_request(db)

            # Store representative recent out-of-fold forecasts (last 30 days)
            recent_count = min(30, len(actuals))
            start_idx = len(actuals) - recent_count

            logger.info("Saving %d recent out-of-fold general forecasts (model_version='v1.1-general-ensemble') and SHAP attributions into Neon...", recent_count)
            for i in range(start_idx, len(actuals)):
                f_record = ForecastResult(
                    request_id=benchmark_req_id,
                    vessel_type_id=None,  # NULL = general dry-bulk market index forecast
                    p10_price=Decimal(f"{p10_arr[i]:.2f}"),
                    p50_price=Decimal(f"{p50_arr[i]:.2f}"),
                    p90_price=Decimal(f"{p90_arr[i]:.2f}"),
                    model_version="v1.1-general-ensemble",
                )
                db.add(f_record)
                db.flush()

                # Compute top 3 SHAP explanations
                single_feat = oof_features[i]
                tree = oof_fitted_trees[i]
                explanations = compute_shap_explanations(tree, single_feat, top_k=3)

                for exp in explanations:
                    exp_record = ShapExplanation(
                        forecast_id=f_record.forecast_id,
                        feature_name=exp.feature_name,
                        contribution_pct=Decimal(f"{exp.contribution_pct:.2f}"),
                        direction=exp.direction,
                    )
                    db.add(exp_record)

            db.commit()

            # Post-insertion assertions
            post_v1_1_count = db.query(ForecastResult).filter(ForecastResult.model_version == "v1.1-general-ensemble").count()
            post_s_count = db.query(ShapExplanation).count()
            if post_v1_1_count != recent_count:
                raise AssertionError(f"Post-insert assertion failed! Expected {recent_count} v1.1 forecasts, found {post_v1_1_count}")
            if post_s_count != recent_count * 3:
                raise AssertionError(f"Post-insert assertion failed! Expected {recent_count * 3} explanations, found {post_s_count}")

            logger.info(
                "Successfully persisted %d ForecastResults (v1.1-general-ensemble) and %d ShapExplanations with vessel_type_id=NULL into Neon.",
                post_v1_1_count,
                post_s_count,
            )
        except Exception as exc:
            db.rollback()
            logger.error("Failed during forecast persistence to Neon: %s", exc)
            raise
        finally:
            db.close()

    return metrics


if __name__ == "__main__":
    results = run_walk_forward_training()
    print(f"SUCCESS: Walk-forward validation complete: {results}")
