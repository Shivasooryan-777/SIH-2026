"""
SHAP Feature Attribution Module
===============================
Extracts top 3 contributing factors per forecast using SHAP TreeExplainer on the
median (P50) tree-based model, per docs/blueprint.md Module A and Section 8.3:
- Table: ShapExplanations (forecast_id, feature_name, contribution_pct, direction)
- Direction: 'upward' (pushes freight rate higher) or 'downward' (pushes rate lower)
- Contribution: relative percentage of total absolute attribution (|phi_i| / sum |phi|)
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("ml.attribution")


@dataclass
class FeatureExplanation:
    """Holds a single feature attribution conforming to ShapExplanations schema."""
    feature_name: str
    contribution_pct: float
    direction: str  # 'upward' or 'downward'


def compute_shap_explanations(
    tree_model: any,
    X_single: pd.DataFrame,
    top_k: int = 3,
) -> List[FeatureExplanation]:
    """
    Compute SHAP attributions for a single observation row.

    Args:
        tree_model: Fitted LightGBM or XGBoost estimator (median P50 model).
        X_single: Single-row DataFrame containing the features for that prediction.
        top_k: Number of top features to return (default: 3).

    Returns:
        List[FeatureExplanation]: Top-k explanations sorted by absolute importance.
    """
    if len(X_single) != 1:
        raise ValueError(f"X_single must contain exactly 1 row, got {len(X_single)}")

    feature_names = list(X_single.columns)

    try:
        import shap

        explainer = shap.TreeExplainer(tree_model)
        shap_values = explainer.shap_values(X_single)

        # Handle different SHAP output formats (list for multiclass/multioutput or 2D array)
        if isinstance(shap_values, list):
            vals = np.asarray(shap_values[0])[0]
        elif isinstance(shap_values, np.ndarray):
            if shap_values.ndim == 2:
                vals = shap_values[0]
            else:
                vals = shap_values
        else:
            vals = np.asarray(shap_values).flatten()

    except Exception as exc:
        logger.warning("SHAP TreeExplainer calculation failed or unavailable (%s). Using feature importance fallback.", exc)
        # Fallback to model feature importances
        if hasattr(tree_model, "feature_importances_"):
            importances = tree_model.feature_importances_
            vals = np.asarray(importances, dtype=float)
        else:
            vals = np.ones(len(feature_names))

    abs_vals = np.abs(vals)
    total_abs = np.sum(abs_vals)
    if total_abs == 0:
        total_abs = 1e-6

    # Rank indices by descending absolute attribution
    ranked_indices = np.argsort(abs_vals)[::-1]
    top_indices = ranked_indices[:top_k]

    explanations: List[FeatureExplanation] = []
    for idx in top_indices:
        feat_name = feature_names[idx]
        val = vals[idx]
        pct = float((abs_vals[idx] / total_abs) * 100.0)
        direction = "upward" if val >= 0 else "downward"

        explanations.append(
            FeatureExplanation(
                feature_name=str(feat_name)[:50],  # VARCHAR(50) per schema
                contribution_pct=round(pct, 2),
                direction=direction,
            )
        )

    return explanations
