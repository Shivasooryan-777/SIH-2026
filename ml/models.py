"""
Quantile Forecasting Models Module
==================================
Implements quantile regression for freight rate forecasting per docs/blueprint.md Module A:
- LightGBM Quantile Regressor: pinball loss (alpha = 0.10, 0.50, 0.90)
- XGBoost Quantile Regressor: 'reg:quantileerror' (quantile_alpha = 0.10, 0.50, 0.90)
- Prophet Seasonal Baseline: interval_width=0.80 (p10, p50, p90)
- Monotonic Ensemble: ensures p10 <= p50 <= p90 unconditionally

HARDWARE SAFETY:
- CPU-only execution (device='cpu', n_jobs=2)
- Conservative tree bounds (max_depth=4, n_estimators=150, early stopping)
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("ml.models")


@dataclass
class QuantileForecast:
    """Holds structured P10, P50, and P90 quantile forecasts."""
    p10: np.ndarray
    p50: np.ndarray
    p90: np.ndarray

    def __post_init__(self):
        # Guarantee strict quantile order: p10 <= p50 <= p90
        self.p10 = np.minimum(self.p10, self.p50)
        self.p90 = np.maximum(self.p90, self.p50)


class LightGBMQuantileModel:
    """
    LightGBM model training three separate quantile regressors (alpha=0.10, 0.50, 0.90).
    """

    def __init__(
        self,
        n_estimators: int = 150,
        max_depth: int = 4,
        num_leaves: int = 15,
        learning_rate: float = 0.05,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
    ):
        self.params = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "num_leaves": num_leaves,
            "learning_rate": learning_rate,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "device": "cpu",
            "n_jobs": 2,
            "verbosity": -1,
            "random_state": 42,
        }
        self.models: Dict[float, Any] = {}

    def fit(self, X_train: pd.DataFrame, y_train: pd.Series) -> "LightGBMQuantileModel":
        import lightgbm as lgb  # type: ignore

        for alpha in [0.10, 0.50, 0.90]:
            model = lgb.LGBMRegressor(
                objective="quantile",
                alpha=alpha,
                **self.params,
            )
            model.fit(X_train, y_train)
            self.models[alpha] = model
        return self

    def predict(self, X_test: pd.DataFrame) -> QuantileForecast:
        p10 = self.models[0.10].predict(X_test)
        p50 = self.models[0.50].predict(X_test)
        p90 = self.models[0.90].predict(X_test)
        return QuantileForecast(p10=np.asarray(p10), p50=np.asarray(p50), p90=np.asarray(p90))


class XGBoostQuantileModel:
    """
    XGBoost model training three separate quantile regressors (alpha=0.10, 0.50, 0.90).
    """

    def __init__(
        self,
        n_estimators: int = 150,
        max_depth: int = 4,
        learning_rate: float = 0.05,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
    ):
        self.params = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "tree_method": "hist",
            "device": "cpu",
            "n_jobs": 2,
            "random_state": 42,
        }
        self.models: Dict[float, Any] = {}

    def fit(self, X_train: pd.DataFrame, y_train: pd.Series) -> "XGBoostQuantileModel":
        import xgboost as xgb  # type: ignore

        for alpha in [0.10, 0.50, 0.90]:
            model = xgb.XGBRegressor(
                objective="reg:quantileerror",
                quantile_alpha=alpha,
                **self.params,
            )
            model.fit(X_train, y_train)
            self.models[alpha] = model
        return self

    def predict(self, X_test: pd.DataFrame) -> QuantileForecast:
        p10 = self.models[0.10].predict(X_test)
        p50 = self.models[0.50].predict(X_test)
        p90 = self.models[0.90].predict(X_test)
        return QuantileForecast(p10=np.asarray(p10), p50=np.asarray(p50), p90=np.asarray(p90))


class ProphetBaselineModel:
    """
    Facebook Prophet seasonal baseline yielding P10, P50, and P90 via interval_width=0.80.
    Falls back to empirical quantile if Prophet is not installed in the environment.
    """

    def __init__(self, interval_width: float = 0.80):
        self.interval_width = interval_width
        self.model = None
        self.train_df: Optional[pd.DataFrame] = None
        self.last_p10 = 0.0
        self.last_p50 = 0.0
        self.last_p90 = 0.0

    def fit(self, dates_train: pd.Series, y_train: pd.Series) -> "ProphetBaselineModel":
        try:
            import logging as _logging
            _logging.getLogger("cmdstanpy").setLevel(_logging.WARNING)
            _logging.getLogger("prophet").setLevel(_logging.WARNING)
            from prophet import Prophet  # type: ignore
            df_prophet = pd.DataFrame({"ds": pd.to_datetime(dates_train), "y": y_train.values})
            self.model = Prophet(
                interval_width=self.interval_width,
                yearly_seasonality=True,
                weekly_seasonality=True,
                daily_seasonality=False,
                changepoint_prior_scale=0.05,
            )
            self.model.fit(df_prophet)
        except Exception as exc:
            logger.info("Prophet engine unavailable or error (%s). Using empirical quantile fallback.", exc)
            self.model = None
            # Compute empirical quantiles from trailing train data
            self.last_p10 = float(np.percentile(y_train, 10))
            self.last_p50 = float(np.percentile(y_train, 50))
            self.last_p90 = float(np.percentile(y_train, 90))
        return self

    def predict(self, dates_test: pd.Series) -> QuantileForecast:
        n = len(dates_test)
        if self.model is not None:
            try:
                future = pd.DataFrame({"ds": pd.to_datetime(dates_test)})
                forecast = self.model.predict(future)
                p10 = forecast["yhat_lower"].values
                p50 = forecast["yhat"].values
                p90 = forecast["yhat_upper"].values
                return QuantileForecast(p10=p10, p50=p50, p90=p90)
            except Exception as e:
                logger.warning("Prophet predict failed (%s), using fallback", e)

        # Fallback baseline
        p10 = np.full(n, self.last_p10)
        p50 = np.full(n, self.last_p50)
        p90 = np.full(n, self.last_p90)
        return QuantileForecast(p10=p10, p50=p50, p90=p90)


class EnsembleQuantileModel:
    """
    Ensemble averaging LightGBM, XGBoost, and Prophet predictions,
    strictly enforcing P10 <= P50 <= P90.
    """

    def __init__(self):
        self.lgbm = LightGBMQuantileModel()
        self.xgb = XGBoostQuantileModel()
        self.prophet = ProphetBaselineModel()

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        dates_train: pd.Series,
    ) -> "EnsembleQuantileModel":
        self.lgbm.fit(X_train, y_train)
        self.xgb.fit(X_train, y_train)
        self.prophet.fit(dates_train, y_train)
        return self

    def predict(
        self,
        X_test: pd.DataFrame,
        dates_test: pd.Series,
        calibration_multiplier: float = 1.0,
    ) -> QuantileForecast:
        f_lgbm = self.lgbm.predict(X_test)
        f_xgb = self.xgb.predict(X_test)
        f_prophet = self.prophet.predict(dates_test)

        # Base bounds: arithmetic mean across model families (un-inflated baseline)
        p10_base = (f_lgbm.p10 + f_xgb.p10 + f_prophet.p10) / 3.0
        p50_base = (f_lgbm.p50 + f_xgb.p50 + f_prophet.p50) / 3.0
        p90_base = (f_lgbm.p90 + f_xgb.p90 + f_prophet.p90) / 3.0

        # Apply bidirectional empirical / conformal calibration scaling (multiplier can tighten or widen)
        p10_calib = p50_base - calibration_multiplier * np.maximum(p50_base - p10_base, 0.0)
        p90_calib = p50_base + calibration_multiplier * np.maximum(p90_base - p50_base, 0.0)

        # Freight prices are strictly non-negative
        p10_calib = np.maximum(p10_calib, 0.0)

        return QuantileForecast(p10=p10_calib, p50=p50_base, p90=p90_calib)
