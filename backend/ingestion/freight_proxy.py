"""
Freight Data Ingestion & Proxy Splicing Pipeline
=================================================
DATA SOURCE NOTICE:
The Breakwave Dry Bulk Shipping ETF (ticker: BDRY) price series fetched via yfinance
is utilized as a free, publicly accessible proxy standing in for the paywalled Baltic
Dry Index (BDI) and proprietary Baltic freight rate benchmarks.

Where historical Baltic Dry Index data is supplied locally via `data/raw/bdi_historical.csv`,
this module splices the historical actual BDI series with the modern BDRY ETF proxy
series into a unified, clean, chronologically validated dataset.

SCALE & NORMALIZATION NOTE:
- BDI is reported in index points (historically 500 – 5,000+ points).
- BDRY ETF is traded in USD per share ($5 – $50/share).
- To prevent artificial 50x level shifts at the splice boundary (2018-03-22), this pipeline
  outputs both the raw `nominal_price` (with `source_series` & `is_proxy` metadata) and a
  continuous `normalized_index_base100` that chains daily returns starting at base 100.

All proxy records are explicitly tagged with `is_proxy=True` and `source_series="BDRY_ETF_PROXY"`.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("freight_ingestion")

# Absolute path resolution relative to repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
BDRY_TICKER = "BDRY"
BDRY_INCEPTION_DATE = "2018-03-22"  # Inception date for BDRY ETF
DEFAULT_RAW_BDI_PATH = REPO_ROOT / "data" / "raw" / "bdi_historical.csv"
DEFAULT_PROCESSED_OUTPUT_PATH = REPO_ROOT / "data" / "processed" / "freight_proxy_series.csv"


def fetch_bdry_data(
    ticker_symbol: str = BDRY_TICKER,
    start_date: str = BDRY_INCEPTION_DATE,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetch historical daily market data for the BDRY ETF via yfinance.

    NOTE: BDRY ETF is a free financial proxy reflecting freight futures contracts
    (Capesize, Panamax, Supramax) and is used as an open proxy for dry bulk freight
    rate trends.

    Args:
        ticker_symbol: Yahoo Finance ticker symbol (default: 'BDRY').
        start_date: Start date string in 'YYYY-MM-DD' format.
        end_date: Optional end date string in 'YYYY-MM-DD' format.

    Returns:
        pd.DataFrame: Cleaned DataFrame with standard columns [date, open, high, low, close, volume].
    """
    logger.info("Fetching %s data from yfinance (start=%s, end=%s)...", ticker_symbol, start_date, end_date or "latest")
    ticker = yf.Ticker(ticker_symbol)
    history = ticker.history(start=start_date, end=end_date, auto_adjust=False)

    if history.empty:
        raise ValueError(f"No historical data returned for ticker '{ticker_symbol}'. Check network connection or ticker symbol.")

    df = history.reset_index()

    # Robust timezone-safe date normalization to YYYY-MM-DD
    if "Date" in df.columns:
        date_col = "Date"
    elif "Datetime" in df.columns:
        date_col = "Datetime"
    else:
        raise KeyError(f"Unexpected date column in yfinance response: {list(df.columns)}")

    raw_dates = pd.to_datetime(df[date_col], errors="coerce")
    if hasattr(raw_dates.dt, "tz") and raw_dates.dt.tz is not None:
        df["date"] = raw_dates.dt.tz_convert(None).dt.strftime("%Y-%m-%d")
    else:
        df["date"] = raw_dates.dt.strftime("%Y-%m-%d")

    # Rename standard price columns to lowercase
    column_mapping = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Adj Close": "adj_close",
        "Volume": "volume",
    }
    df = df.rename(columns=column_mapping)

    keep_cols = ["date", "open", "high", "low", "close", "volume"]
    available_cols = [c for c in keep_cols if c in df.columns]
    df = df[available_cols].copy()

    # Drop any rows with NaN in date or close
    df = df.dropna(subset=["date", "close"]).sort_values("date").reset_index(drop=True)
    logger.info("Retrieved %d records for %s from %s to %s", len(df), ticker_symbol, df["date"].min(), df["date"].max())
    return df


def load_historical_bdi(raw_csv_path: Path = DEFAULT_RAW_BDI_PATH) -> Optional[pd.DataFrame]:
    """
    Load historical Baltic Dry Index data from a local raw CSV file if provided.

    Expected CSV columns:
      - 'date' (YYYY-MM-DD)
      - 'bdi_close' or 'close' (float)

    Returns:
        pd.DataFrame if file exists and valid, None otherwise.
    """
    path = Path(raw_csv_path)
    if not path.exists():
        logger.info("No raw historical BDI file found at '%s'. Pipeline will operate on BDRY ETF proxy data.", path)
        return None

    try:
        df = pd.read_csv(path)
        if df.empty:
            logger.warning("Historical BDI file at '%s' is empty. Skipping raw BDI ingestion.", path)
            return None

        # Normalize column names to lowercase stripped
        df.columns = [c.strip().lower() for c in df.columns]

        if "date" not in df.columns:
            logger.error("Historical BDI CSV missing required 'date' column. Found columns: %s", list(df.columns))
            return None

        # Identify close column
        close_col = None
        for candidate in ["bdi_close", "close", "bdi", "value", "index_value"]:
            if candidate in df.columns:
                close_col = candidate
                break

        if close_col is None:
            logger.error("Historical BDI CSV missing closing price column ('bdi_close' or 'close').")
            return None

        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        df["close"] = pd.to_numeric(df[close_col], errors="coerce")
        df = df.dropna(subset=["date", "close"]).sort_values("date").drop_duplicates(subset=["date"]).reset_index(drop=True)

        logger.info("Successfully loaded %d historical BDI records from '%s' (%s to %s)", len(df), path, df["date"].min(), df["date"].max())
        return pd.DataFrame({"date": df["date"], "close": df["close"]})

    except Exception as exc:
        logger.error("Error reading raw historical BDI file '%s': %s", path, exc)
        return None


def splice_freight_series(
    bdry_df: pd.DataFrame,
    bdi_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Splice historical BDI and BDRY ETF proxy into a unified, documented time series.

    PROVENANCE & PROXY RULES:
    1. For dates where actual historical BDI data exists prior to the BDRY ETF inception,
       the series uses actual BDI records tagged with:
         - `source_series = "BDI_HISTORICAL"`
         - `is_proxy = False`
    2. For dates from BDRY ETF availability onwards, the series uses BDRY ETF prices tagged with:
         - `source_series = "BDRY_ETF_PROXY"`
         - `is_proxy = True`
    3. The BDRY proxy price stands in for dry bulk freight market movements where proprietary
       Baltic Exchange data is not licensed/available.
    4. Splicing scale handling:
       - `nominal_price`: raw nominal value ($/share for BDRY, points for BDI).
       - `freight_proxy_value`: primary value column aligned with nominal_price.
       - `normalized_index_base100`: continuous rebased index chained on daily percentage returns,
         preventing level cliffs across the transition boundary.

    Args:
        bdry_df: DataFrame of BDRY ETF prices.
        bdi_df: Optional DataFrame of historical BDI prices.

    Returns:
        pd.DataFrame: Spliced, sorted, deduplicated time series.
    """
    bdry_clean = bdry_df.copy()
    bdry_clean["source_series"] = "BDRY_ETF_PROXY"
    bdry_clean["is_proxy"] = True
    bdry_clean["nominal_price"] = bdry_clean["close"].astype(float)
    bdry_clean["freight_proxy_value"] = bdry_clean["close"].astype(float)

    if bdi_df is None or bdi_df.empty:
        logger.info("Operating purely on BDRY ETF proxy series (no historical BDI provided).")
        raw_result = bdry_clean
    else:
        # Determine splice point: take historical BDI strictly before earliest BDRY date
        bdry_start_date = bdry_clean["date"].min()
        bdi_prior = bdi_df[bdi_df["date"] < bdry_start_date].copy()

        if not bdi_prior.empty:
            logger.info(
                "Splicing %d historical BDI records (pre-%s) with %d BDRY ETF proxy records.",
                len(bdi_prior),
                bdry_start_date,
                len(bdry_clean),
            )
            bdi_prior["source_series"] = "BDI_HISTORICAL"
            bdi_prior["is_proxy"] = False
            bdi_prior["nominal_price"] = bdi_prior["close"].astype(float)
            bdi_prior["freight_proxy_value"] = bdi_prior["close"].astype(float)

            # Ensure schema compatibility for concatenation
            if "open" not in bdi_prior.columns:
                bdi_prior["open"] = bdi_prior["close"]
            if "high" not in bdi_prior.columns:
                bdi_prior["high"] = bdi_prior["close"]
            if "low" not in bdi_prior.columns:
                bdi_prior["low"] = bdi_prior["close"]
            if "volume" not in bdi_prior.columns:
                bdi_prior["volume"] = 0.0

            raw_result = pd.concat([bdi_prior, bdry_clean], ignore_index=True)
        else:
            logger.info("All historical BDI dates overlap or post-date BDRY start date. Using BDRY series.")
            raw_result = bdry_clean

    # Clean, sort, and deduplicate with explicit DataFrame type
    result = pd.DataFrame(raw_result)
    result = (
        result.drop_duplicates(subset=["date"])
        .sort_values("date")
        .reset_index(drop=True)
    )

    # Compute continuous rebased index (base 100 at start of series) using daily returns
    daily_returns = result["nominal_price"].pct_change().fillna(0.0)
    # At the exact splice boundary, set return to 0.0 to avoid an artificial return spike
    is_transition = (result["is_proxy"] != result["is_proxy"].shift(1)) & (result.index > 0)
    daily_returns = daily_returns.mask(is_transition, 0.0)
    result["daily_return"] = daily_returns
    result["normalized_index_base100"] = 100.0 * (1.0 + daily_returns).cumprod()

    # Validate output series integrity
    if result["freight_proxy_value"].isnull().any():
        raise ValueError("Detected null values in freight_proxy_value after splicing.")

    bdi_count = int(np.count_nonzero((~result["is_proxy"]).to_numpy()))
    bdry_count = int(np.count_nonzero(result["is_proxy"].to_numpy()))
    logger.info(
        "Freight proxy series prepared: %d total records spanning %s to %s (%d actual BDI, %d BDRY proxy)",
        len(result),
        result["date"].min(),
        result["date"].max(),
        bdi_count,
        bdry_count,
    )
    return result


def save_processed_data(
    df: pd.DataFrame,
    output_path: Path = DEFAULT_PROCESSED_OUTPUT_PATH,
) -> Path:
    """
    Save the processed freight series to a local CSV in `data/processed/`.

    Args:
        df: Processed DataFrame.
        output_path: Destination path for the CSV.

    Returns:
        Path: Output path written.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    logger.info("Saved processed freight time series to '%s'", path)
    return path


def run_pipeline(
    raw_bdi_path: Path = DEFAULT_RAW_BDI_PATH,
    output_path: Path = DEFAULT_PROCESSED_OUTPUT_PATH,
    start_date: str = BDRY_INCEPTION_DATE,
) -> pd.DataFrame:
    """
    Execute the full end-to-end ingestion and splicing pipeline.
    """
    logger.info("Starting freight data ingestion pipeline...")
    bdry_df = fetch_bdry_data(start_date=start_date)
    bdi_df = load_historical_bdi(raw_csv_path=raw_bdi_path)
    spliced_df = splice_freight_series(bdry_df=bdry_df, bdi_df=bdi_df)
    save_processed_data(spliced_df, output_path=output_path)
    return spliced_df


def main():
    """CLI entry point for unattended / scheduled execution."""
    parser = argparse.ArgumentParser(
        description="Ingest BDRY ETF proxy data via yfinance and splice with historical BDI data."
    )
    parser.add_argument(
        "--raw-bdi",
        type=str,
        default=str(DEFAULT_RAW_BDI_PATH),
        help=f"Path to raw historical BDI CSV file (default: {DEFAULT_RAW_BDI_PATH})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_PROCESSED_OUTPUT_PATH),
        help=f"Path for output processed CSV (default: {DEFAULT_PROCESSED_OUTPUT_PATH})",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=BDRY_INCEPTION_DATE,
        help=f"Start date for BDRY ETF pull (default: {BDRY_INCEPTION_DATE})",
    )

    args = parser.parse_args()

    try:
        run_pipeline(
            raw_bdi_path=Path(args.raw_bdi),
            output_path=Path(args.output),
            start_date=args.start_date,
        )
        logger.info("Ingestion pipeline completed successfully.")
        sys.exit(0)
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
