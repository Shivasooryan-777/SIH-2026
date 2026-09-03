"""
Walk-Forward (Rolling-Origin) Cross-Validation Module
=====================================================
Strict rolling-origin cross-validation engine adhering to docs/blueprint.md Module A:
- Train on [T0..T1], test on [T1..T1+30 days]
- Train on [T0..T1+30], test on [T1+30..T1+60 days]
- Expand forward through the full historical window
- Explicitly forbids random k-fold or naive in-sample splits to eliminate temporal leakage.
"""

from dataclasses import dataclass
from typing import Generator, List, Optional, Tuple
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class WalkForwardFold:
    """Represents a single walk-forward cross-validation fold."""
    fold_idx: int
    train_indices: np.ndarray
    test_indices: np.ndarray
    train_start_date: str
    train_end_date: str
    test_start_date: str
    test_end_date: str

    @property
    def train_size(self) -> int:
        return len(self.train_indices)

    @property
    def test_size(self) -> int:
        return len(self.test_indices)


def validate_no_leakage(
    df: pd.DataFrame,
    train_indices: np.ndarray,
    test_indices: np.ndarray,
    date_col: str = "date",
) -> None:
    """
    Formally verify that no test-period data or indices leak into the training set.

    Raises:
        ValueError: If index intersection is non-empty or temporal ordering is violated.
    """
    train_idx_set = set(train_indices)
    test_idx_set = set(test_indices)
    overlap = train_idx_set.intersection(test_idx_set)
    if overlap:
        raise ValueError(
            f"LEAKAGE DETECTED: Index overlap found between train and test sets! "
            f"Overlapping indices count: {len(overlap)}"
        )

    if date_col in df.columns:
        train_dates = pd.to_datetime(df.iloc[train_indices][date_col])
        test_dates = pd.to_datetime(df.iloc[test_indices][date_col])

        max_train_date = train_dates.max()
        min_test_date = test_dates.min()

        if max_train_date >= min_test_date:
            raise ValueError(
                f"TEMPORAL LEAKAGE DETECTED: Maximum training date ({max_train_date}) "
                f"is not strictly before minimum test date ({min_test_date})!"
            )


def generate_walk_forward_splits(
    df: pd.DataFrame,
    min_train_size: int = 500,
    test_horizon: int = 30,
    step_size: int = 30,
    date_col: str = "date",
) -> List[WalkForwardFold]:
    """
    Generate rolling-origin walk-forward folds across a time series DataFrame.

    Args:
        df: Input DataFrame sorted strictly by date ascending.
        min_train_size: Minimum number of rows for initial training origin [T0..T1].
        test_horizon: Number of forward testing steps [T1..T1+test_horizon].
        step_size: Step size to advance the origin for the next fold.
        date_col: Column name containing date values.

    Returns:
        List[WalkForwardFold]: List of validated walk-forward folds.
    """
    total_rows = len(df)
    if total_rows < min_train_size + test_horizon:
        raise ValueError(
            f"Insufficient data for walk-forward CV: total_rows={total_rows}, "
            f"min_train_size={min_train_size}, test_horizon={test_horizon}"
        )

    folds: List[WalkForwardFold] = []
    current_origin = min_train_size
    fold_idx = 0

    all_indices = np.arange(total_rows)

    while current_origin + test_horizon <= total_rows:
        train_indices = all_indices[:current_origin]
        test_indices = all_indices[current_origin : current_origin + test_horizon]

        # Verify strict non-leakage invariant
        validate_no_leakage(df, train_indices, test_indices, date_col=date_col)

        train_start = str(df.iloc[train_indices[0]][date_col]) if date_col in df.columns else f"idx_{train_indices[0]}"
        train_end = str(df.iloc[train_indices[-1]][date_col]) if date_col in df.columns else f"idx_{train_indices[-1]}"
        test_start = str(df.iloc[test_indices[0]][date_col]) if date_col in df.columns else f"idx_{test_indices[0]}"
        test_end = str(df.iloc[test_indices[-1]][date_col]) if date_col in df.columns else f"idx_{test_indices[-1]}"

        folds.append(
            WalkForwardFold(
                fold_idx=fold_idx,
                train_indices=train_indices,
                test_indices=test_indices,
                train_start_date=train_start,
                train_end_date=train_end,
                test_start_date=test_start,
                test_end_date=test_end,
            )
        )

        current_origin += step_size
        fold_idx += 1

    return folds
