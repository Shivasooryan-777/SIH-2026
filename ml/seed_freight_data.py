"""
Freight Rate Data Seeding & Cleanup Utility (Honest Scoping - Option 2)
======================================================================
Populates the Neon Postgres 'freight_rate_data' table using the single, unscaled,
verifiable BDRY ETF proxy time series (data/processed/freight_proxy_series.csv).

HONEST DATA PROVENANCE NOTICE:
- Uses the single real BDRY ETF proxy series (2018–present).
- vessel_type_id is set to NULL, explicitly defining this as a general dry-bulk market series.
- Synthetic vessel-class multipliers ($22k/$15k/$12.5k/$9.5k) are permanently eliminated.
- Column value_usd_per_day holds the raw BDRY ETF proxy closing price in USD/share,
  NOT a literal vessel charter hire rate in USD/day.
"""

import argparse
import logging
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy.orm import Session

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.database import SessionLocal
from backend.app.models import ForecastResult, FreightRateData, ShapExplanation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ml.seed_freight_data")

DEFAULT_PROCESSED_SERIES = REPO_ROOT / "data" / "processed" / "freight_proxy_series.csv"


def cleanup_fabricated_and_old_records(db: Session) -> Dict[str, int]:
    """
    Explicitly delete the 8,492 fabricated freight rate rows and the
    Session 5 test forecasts and explanations before re-seeding the real series.

    Strict assertion gates:
    - Pre-delete: verifies freight_rate_data count is exactly 8,492.
    - Post-delete: asserts deleted counts match exactly (8,492 freight, 30 forecasts, 90 explanations).
    """
    logger.info("Executing deletion of Session 5 fabricated data...")

    # Pre-condition assertion: exactly 8,492 rows must be present
    pre_freight_count = db.query(FreightRateData).count()
    if pre_freight_count != 8492:
        raise AssertionError(
            f"Pre-delete assertion failed! Expected exactly 8492 rows in freight_rate_data, "
            f"found {pre_freight_count}. Aborting deletion."
        )

    # Step 1: Identify Session 5 forecast IDs to safely clean child explanations
    s5_forecast_ids = [
        r[0]
        for r in db.query(ForecastResult.forecast_id)
        .filter(ForecastResult.model_version == "v1.0-ensemble")
        .all()
    ]

    # Step 2: Delete child ShapExplanations (must equal 90)
    deleted_shap = 0
    if s5_forecast_ids:
        deleted_shap = (
            db.query(ShapExplanation)
            .filter(ShapExplanation.forecast_id.in_(s5_forecast_ids))
            .delete(synchronize_session=False)
        )

    # Step 3: Delete parent ForecastResults (must equal 30)
    deleted_forecasts = (
        db.query(ForecastResult)
        .filter(ForecastResult.model_version == "v1.0-ensemble")
        .delete(synchronize_session=False)
    )

    # Step 4: Delete all 8,492 fabricated rows from FreightRateData
    deleted_freight = db.query(FreightRateData).delete(synchronize_session=False)

    # Commit transaction
    db.commit()

    logger.info(
        "Deletion executed: %d freight_rate_data, %d forecast_results, %d shap_explanations",
        deleted_freight,
        deleted_forecasts,
        deleted_shap,
    )

    # Post-condition assertions: fail loudly if any count does not match exactly
    if deleted_freight != 8492:
        raise AssertionError(
            f"Post-delete assertion failed! Expected exactly 8492 deleted freight rows, got {deleted_freight}"
        )
    if deleted_forecasts != 30:
        raise AssertionError(
            f"Post-delete assertion failed! Expected exactly 30 deleted forecast rows, got {deleted_forecasts}"
        )
    if deleted_shap != 90:
        raise AssertionError(
            f"Post-delete assertion failed! Expected exactly 90 deleted shap explanation rows, got {deleted_shap}"
        )

    return {
        "freight_rate_data_deleted": deleted_freight,
        "forecast_results_deleted": deleted_forecasts,
        "shap_explanations_deleted": deleted_shap,
    }


def seed_single_real_series(
    db: Session,
    csv_path: Path = DEFAULT_PROCESSED_SERIES,
    batch_size: int = 1000,
) -> int:
    """
    Insert the single real BDRY trading-day series (2,123 rows) into Neon freight_rate_data.
    - vessel_type_id is explicitly set to NULL (indicating a general dry-bulk market index).
    - value_usd_per_day holds the raw, unscaled BDRY ETF proxy price in USD/share from Yahoo Finance.
    - Zero multipliers or synthetic adjustments are applied.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Processed freight series not found at {path}")

    df = pd.read_csv(path)
    if df.empty:
        raise ValueError("Processed freight series is empty!")

    to_insert: List[dict] = []
    for _, row in df.iterrows():
        parsed_date = datetime.strptime(str(row["date"]), "%Y-%m-%d").date()
        raw_price = float(row["freight_proxy_value"])

        to_insert.append({
            "date": parsed_date,
            "vessel_type_id": None,  # NULL = general dry-bulk market series (not vessel-specific)
            "index_type": "BDRY_proxy",
            # NOTE: For index_type='BDRY_proxy' rows, this column holds the raw BDRY ETF proxy value
            # (unscaled USD/share from Yahoo Finance), NOT a literal vessel charter rate in USD/day
            # — to prevent future confusion about what that number means.
            "value_usd_per_day": Decimal(f"{raw_price:.2f}"),
            "source": "BDRY_ETF_PROXY",
        })

    logger.info("Inserting %d single real freight rate records in batches of %d...", len(to_insert), batch_size)
    for i in range(0, len(to_insert), batch_size):
        batch = to_insert[i : i + batch_size]
        db.bulk_insert_mappings(FreightRateData, batch)
        db.commit()

    total_in_db = db.query(FreightRateData).count()
    if total_in_db != len(to_insert):
        raise AssertionError(
            f"Post-seed assertion failed! Expected {len(to_insert)} total rows in freight_rate_data, got {total_in_db}"
        )

    logger.info("FreightRateData honest seeding complete. Total rows in table: %d (all vessel_type_id=NULL)", total_in_db)
    return total_in_db


def reseed_honest_freight_data(csv_path: Path = DEFAULT_PROCESSED_SERIES) -> Dict[str, int]:
    """
    Full pipeline: clean up fabricated data with strict assertions, then re-seed the single real series.
    """
    db = SessionLocal()
    try:
        cleanup_stats = cleanup_fabricated_and_old_records(db)
        inserted_count = seed_single_real_series(db, csv_path=csv_path)
        return {
            **cleanup_stats,
            "freight_rate_data_reseeded": inserted_count,
        }
    except Exception as exc:
        db.rollback()
        logger.error("Failed during honest re-seeding: %s", exc, exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean up fabricated data and re-seed single honest series.")
    parser.add_argument("--reseed-real-only", action="store_true", help="Execute cleanup and honest re-seed")
    args = parser.parse_args()

    result = reseed_honest_freight_data()
    print(f"SUCCESS: Honest re-seed complete: {result}")
