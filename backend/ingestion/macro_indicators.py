"""
Macro Indicator Ingestion & Database Seeding Pipeline
=====================================================
DATA SOURCE NOTICE & PROXY DISCLOSURE:
Fetches macroeconomic and commodity time series via yfinance as leading indicator
features for the freight forecasting model (Module A):
1. Brent Crude Oil Futures (ticker: BZ=F) -> indicator_type: 'brent_crude'
   Direct commodity futures contract tracking global energy and bunker fuel cost trends.
2. USD/INR Exchange Rate (ticker: INR=X) -> indicator_type: 'usd_inr'
   Forex benchmark capturing currency volatility for overseas procurement landed costs.
3. Peabody Energy Corporation (ticker: BTU) -> indicator_type: 'coal_futures'
   Equity proxy for international seaborne thermal and metallurgical coal export prices.
4. Vale S.A. (ticker: VALE) -> indicator_type: 'iron_ore'
   Equity proxy for global seaborne iron ore prices.

COMMODITY PROXY LIMITATION DISCLOSURE:
VALE and BTU are company equity prices used as commodity-price proxies because yfinance
has no continuous coal or iron-ore futures ticker available. Unlike BDRY (a freight-tracking
fund) or Brent crude (a direct commodity future), equity prices carry company-specific noise
(operational, financial, and market equity sentiment) in addition to commodity price signal.
This is a disclosed, transparent limitation, not implied equivalence to a real futures price.

DATA INTEGRITY & QUALITY STANDARDS:
- Non-null dates and closing values
- Normalized YYYY-MM-DD date format
- Strict ascending chronological sort
- Deduplicated by (date, indicator_type)
- Output shaped to match MacroIndicators schema: (date, indicator_type, value)
- Idempotent insertion into Neon Postgres (safe to run repeatedly)
"""

import argparse
import logging
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.database import SessionLocal
from backend.app.models import MacroIndicator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("macro_ingestion")

# Start date aligned with BDRY ETF inception to maintain consistent feature matrix
DEFAULT_START_DATE = "2018-03-22"
DEFAULT_PROCESSED_OUTPUT_PATH = REPO_ROOT / "data" / "processed" / "macro_indicators_series.csv"

# Ingestion configuration mapping
MACRO_TICKERS: Dict[str, Dict[str, str]] = {
    "brent_crude": {
        "ticker": "BZ=F",
        "description": "Brent Crude Oil Futures (energy/bunker benchmark)",
    },
    "usd_inr": {
        "ticker": "INR=X",
        "description": "USD to INR Exchange Rate (procurement currency proxy)",
    },
    "coal_futures": {
        "ticker": "BTU",
        "description": "Peabody Energy (international seaborne coal equity proxy)",
    },
    "iron_ore": {
        "ticker": "VALE",
        "description": "Vale S.A. (global seaborne iron ore equity proxy)",
    },
}


def fetch_indicator_series(
    indicator_type: str,
    ticker_symbol: str,
    start_date: str = DEFAULT_START_DATE,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetch and clean a single macro indicator series via yfinance.

    Args:
        indicator_type: Canonical indicator label ('brent_crude', 'usd_inr', 'coal_futures').
        ticker_symbol: Yahoo Finance ticker (e.g., 'BZ=F', 'INR=X', 'NCF=F').
        start_date: Historical start date string (YYYY-MM-DD).
        end_date: Optional end date string (YYYY-MM-DD).

    Returns:
        pd.DataFrame: Cleaned DataFrame with ['date', 'indicator_type', 'value', 'ticker'].
    """
    logger.info("Fetching '%s' (%s) from yfinance (start=%s)...", indicator_type, ticker_symbol, start_date)
    ticker = yf.Ticker(ticker_symbol)
    history = ticker.history(start=start_date, end=end_date, auto_adjust=False)

    if history.empty:
        raise ValueError(
            f"No data returned for ticker '{ticker_symbol}' ({indicator_type}). "
            f"Check network connectivity or ticker validity."
        )

    df = history.reset_index()

    # Timezone-safe date normalization to YYYY-MM-DD
    if "Date" in df.columns:
        date_col = "Date"
    elif "Datetime" in df.columns:
        date_col = "Datetime"
    else:
        raise KeyError(f"Unexpected date column in yfinance response for {ticker_symbol}: {list(df.columns)}")

    raw_dates = pd.to_datetime(df[date_col], errors="coerce")
    if hasattr(raw_dates.dt, "tz") and raw_dates.dt.tz is not None:
        df["date"] = raw_dates.dt.tz_convert(None).dt.strftime("%Y-%m-%d")
    else:
        df["date"] = raw_dates.dt.strftime("%Y-%m-%d")

    # Select closing price
    close_col = "Close" if "Close" in df.columns else "close"
    if close_col not in df.columns:
        raise KeyError(f"Missing closing price column in yfinance response for {ticker_symbol}")

    df["value"] = pd.to_numeric(df[close_col], errors="coerce")
    df["indicator_type"] = indicator_type
    df["ticker"] = ticker_symbol

    # Data quality filters: drop null dates or values, positive values only
    cleaned = (
        df[["date", "indicator_type", "value", "ticker"]]
        .dropna(subset=["date", "value"])
        .query("value > 0")
        .drop_duplicates(subset=["date"])
        .sort_values("date")
        .reset_index(drop=True)
    )

    logger.info(
        "Successfully retrieved %d records for '%s' (%s to %s)",
        len(cleaned),
        indicator_type,
        cleaned["date"].min(),
        cleaned["date"].max(),
    )
    return cleaned


def fetch_all_macro_indicators(
    start_date: str = DEFAULT_START_DATE,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetch all configured macro indicator series and concatenate into a single DataFrame.
    """
    series_list: List[pd.DataFrame] = []

    for ind_type, conf in MACRO_TICKERS.items():
        df_ind = fetch_indicator_series(
            indicator_type=ind_type,
            ticker_symbol=conf["ticker"],
            start_date=start_date,
            end_date=end_date,
        )
        series_list.append(df_ind)

    combined = pd.concat(series_list, ignore_index=True)
    combined = combined.sort_values(["indicator_type", "date"]).reset_index(drop=True)

    # Validate overall integrity
    assert not combined["value"].isnull().any(), "Found null values in combined macro series!"
    assert not combined["date"].isnull().any(), "Found null dates in combined macro series!"

    logger.info(
        "Total macro records ingested: %d across %d indicators",
        len(combined),
        len(MACRO_TICKERS),
    )
    return combined


def save_processed_macro_data(
    df: pd.DataFrame,
    output_path: Path = DEFAULT_PROCESSED_OUTPUT_PATH,
) -> Path:
    """
    Save the combined macro indicators series to data/processed/.
    NOTE: Does NOT touch data/processed/freight_proxy_series.csv.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    logger.info("Saved processed macro indicator series to '%s'", path)
    return path


def seed_macro_indicators_to_db(
    df: pd.DataFrame,
    batch_size: int = 1000,
) -> Tuple[int, int]:
    """
    Insert macro indicator records into the Neon 'macro_indicators' table.
    Ensures idempotency by checking existing (date, indicator_type) pairs.

    Returns:
        Tuple[int, int]: (inserted_count, skipped_count)
    """
    logger.info("Seeding macro indicators into Neon database...")
    db = SessionLocal()

    try:
        # Load existing (date, indicator_type) pairs for natural-key idempotency
        existing_records = db.query(MacroIndicator.date, MacroIndicator.indicator_type).all()
        existing_keys: Set[Tuple[str, str]] = {
            (r[0].strftime("%Y-%m-%d") if hasattr(r[0], "strftime") else str(r[0]), str(r[1]))
            for r in existing_records
        }
        logger.info("Found %d existing records in 'macro_indicators' table.", len(existing_keys))

        to_insert: List[dict] = []
        skipped_count = 0

        for _, row in df.iterrows():
            row_date_str = str(row["date"])
            row_ind_type = str(row["indicator_type"])
            key = (row_date_str, row_ind_type)

            if key in existing_keys:
                skipped_count += 1
                continue

            parsed_date = datetime.strptime(row_date_str, "%Y-%m-%d").date()
            to_insert.append({
                "date": parsed_date,
                "indicator_type": row_ind_type,
                "value": Decimal(f"{float(row['value']):.4f}"),
            })

        inserted_count = 0
        if to_insert:
            logger.info("Inserting %d new macro indicator records in batches of %d...", len(to_insert), batch_size)
            for i in range(0, len(to_insert), batch_size):
                batch = to_insert[i : i + batch_size]
                db.bulk_insert_mappings(MacroIndicator, batch)
                db.commit()
                inserted_count += len(batch)
                logger.info("  Committed batch %d/%d (%d rows)", i // batch_size + 1, (len(to_insert) + batch_size - 1) // batch_size, inserted_count)
        else:
            logger.info("All %d records already exist in database. Zero duplicates inserted.", len(df))

        total_in_db = db.query(MacroIndicator).count()
        logger.info("Macro indicators database seeding complete: %d inserted, %d skipped. Total in DB: %d",
                    inserted_count, skipped_count, total_in_db)
        return inserted_count, skipped_count

    except Exception as exc:
        db.rollback()
        logger.error("Failed to seed macro indicators to database: %s", exc, exc_info=True)
        raise
    finally:
        db.close()


def run_macro_pipeline(
    start_date: str = DEFAULT_START_DATE,
    output_path: Path = DEFAULT_PROCESSED_OUTPUT_PATH,
    seed_db: bool = True,
) -> pd.DataFrame:
    """
    Execute full ingestion and optional database seeding pipeline.
    """
    df = fetch_all_macro_indicators(start_date=start_date)
    save_processed_macro_data(df, output_path=output_path)
    if seed_db:
        seed_macro_indicators_to_db(df)
    return df


def main():
    """CLI entry point for macro indicator ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest macro indicators (Brent crude, USD/INR, Newcastle Coal) via yfinance."
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=DEFAULT_START_DATE,
        help=f"Historical start date (default: {DEFAULT_START_DATE})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_PROCESSED_OUTPUT_PATH),
        help=f"Path for output CSV (default: {DEFAULT_PROCESSED_OUTPUT_PATH})",
    )
    parser.add_argument(
        "--seed-db",
        action="store_true",
        default=False,
        help="Seed processed data into Neon database table 'macro_indicators'",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        default=False,
        help="Run full pipeline: fetch, save CSV, and seed to database",
    )

    args = parser.parse_args()

    try:
        seed = args.seed_db or args.all
        run_macro_pipeline(
            start_date=args.start_date,
            output_path=Path(args.output),
            seed_db=seed,
        )
        logger.info("Macro indicator ingestion pipeline finished successfully.")
        sys.exit(0)
    except Exception as exc:
        logger.error("Macro pipeline failed: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
