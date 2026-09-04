"""
Module C — Risk Radar Engine
============================
Implements quantitative market volatility tracking, historical disruption replay,
and proactive route risk flagging per docs/blueprint.md Module C:

1. Volatility Metric & Thresholds:
   - 14-day rolling annualized standard deviation of daily freight returns:
     sigma_ann = std(r_14) * sqrt(252) * 100%
   - 7-day price rate-of-change:
     ROC_7 = (P_t - P_{t-7}) / P_{t-7} * 100%

   Thresholds:
   - CALM:     sigma_ann < 60% AND |ROC_7| < 12%
   - ELEVATED: 60% <= sigma_ann < 85% OR 12% <= |ROC_7| < 20% (or active medium disruption)
   - HIGH:     sigma_ann >= 85% OR |ROC_7| >= 20% OR active high-severity disruption

2. Historical Replay Backtest:
   Validates by replaying curated RiskEvents (Suez 2021, Red Sea 2023, Cyclone Idai 2019,
   Australian congestion 2024) to confirm rule-based detection in advance or concurrently.

3. RiskFlags Persistence:
   Writes and serves route-level risk flags (calm/elevated/high) with plain-language explanations.
"""

import logging
from datetime import date as DateType, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple, cast

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from backend.app.models import FreightRateData, RiskEvent, RiskFlag, Route

logger = logging.getLogger("backend.services.risk_radar")

REPO_ROOT = Path(__file__).resolve().parents[3]

# Quantitative Threshold Constants
VOL_THRESHOLD_ELEVATED = 60.0  # Annualized volatility %
VOL_THRESHOLD_HIGH = 85.0
ROC_THRESHOLD_ELEVATED = 12.0  # 7-day price rate of change %
ROC_THRESHOLD_HIGH = 20.0


def load_freight_series_for_volatility(
    db: Optional[Session] = None,
) -> pd.DataFrame:
    """
    Load chronological daily freight rate data (BDRY proxy, vessel_type_id=NULL).
    Queries Neon DB first; falls back to local processed CSV.
    """
    if db is not None:
        try:
            rows = (
                db.query(FreightRateData.date, FreightRateData.value_usd_per_day)
                .filter(FreightRateData.vessel_type_id.is_(None))
                .order_by(FreightRateData.date.asc())
                .all()
            )
            if len(rows) >= 60:
                df = pd.DataFrame([{"date": str(r[0]), "price": float(r[1])} for r in rows])
                df["date"] = pd.to_datetime(df["date"])
                return df.sort_values("date").drop_duplicates(subset=["date"]).reset_index(drop=True)
        except Exception as exc:
            logger.warning("DB query failed (%s), falling back to local freight CSV.", exc)

    csv_path = REPO_ROOT / "data" / "processed" / "freight_proxy_series.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing processed freight CSV: {csv_path}")

    raw_df = pd.read_csv(csv_path)
    price_col = "freight_proxy_value" if "freight_proxy_value" in raw_df else "close"
    df = pd.DataFrame({
        "date": pd.to_datetime(raw_df["date"]),
        "price": raw_df[price_col].astype(float),
    })
    return df.sort_values("date").drop_duplicates(subset=["date"]).reset_index(drop=True)


def compute_market_volatility(
    eval_date: DateType,
    freight_df: Optional[pd.DataFrame] = None,
    lookback_days: int = 14,
    db: Optional[Session] = None,
) -> Dict[str, float]:
    """
    Compute 14-day rolling annualized volatility and 7-day rate-of-change strictly
    using observations on or before eval_date (zero future lookahead).
    """
    if freight_df is None:
        freight_df = load_freight_series_for_volatility(db=db)

    eval_dt = pd.to_datetime(eval_date)
    history = freight_df[freight_df["date"] <= eval_dt].copy()

    if len(history) < lookback_days + 7:
        return {
            "price": 15.0,
            "sigma_ann_pct": 30.0,
            "roc_7_pct": 0.0,
            "daily_sigma_pct": 1.9,
        }

    prices = np.asarray(history["price"], dtype=float)
    current_price = float(prices[-1])

    # 1. 14-day daily returns
    recent_prices = prices[-(lookback_days + 1):]
    returns = np.diff(recent_prices) / recent_prices[:-1]
    daily_sigma = float(np.std(returns, ddof=1)) if len(returns) > 1 else 0.0
    sigma_ann_pct = daily_sigma * np.sqrt(252.0) * 100.0

    # 2. 7-day rate of change: (P_t - P_{t-7}) / P_{t-7}
    p_t = prices[-1]
    p_t7 = prices[-8] if len(prices) >= 8 else prices[0]
    roc_7_pct = float((p_t - p_t7) / (p_t7 + 1e-6) * 100.0)

    return {
        "price": current_price,
        "sigma_ann_pct": round(sigma_ann_pct, 2),
        "roc_7_pct": round(roc_7_pct, 2),
        "daily_sigma_pct": round(daily_sigma * 100.0, 2),
    }


def classify_risk_level(
    sigma_ann_pct: float,
    roc_7_pct: float,
    active_disruption: Optional[RiskEvent] = None,
) -> Tuple[str, str]:
    """
    Classify risk level into CALM, ELEVATED, or HIGH and construct a plain-language reason.
    """
    # 1. High Disruption Trigger
    if active_disruption and active_disruption.severity_level == "high":
        reason = (
            f"HIGH RISK — Active disruption alert: {active_disruption.description} "
            f"(Event: {active_disruption.event_type}). Annualized freight volatility is "
            f"{sigma_ann_pct:.1f}% with 7-day price momentum of {roc_7_pct:+.1f}%."
        )
        return "high", reason

    if sigma_ann_pct >= VOL_THRESHOLD_HIGH or abs(roc_7_pct) >= ROC_THRESHOLD_HIGH:
        reasons = []
        if sigma_ann_pct >= VOL_THRESHOLD_HIGH:
            reasons.append(f"14-day volatility {sigma_ann_pct:.1f}% exceeds high threshold ({VOL_THRESHOLD_HIGH}%)")
        if abs(roc_7_pct) >= ROC_THRESHOLD_HIGH:
            reasons.append(f"7-day price move {roc_7_pct:+.1f}% exceeds surge threshold ({ROC_THRESHOLD_HIGH}%)")
        reason = f"HIGH RISK — Market turbulence detected: {'; '.join(reasons)}. Caution margin widened."
        return "high", reason

    # 2. Elevated Disruption Trigger
    if active_disruption and active_disruption.severity_level in ("medium", "low"):
        reason = (
            f"ELEVATED RISK — Regional disruption alert: {active_disruption.description} "
            f"(Severity: {active_disruption.severity_level}). Volatility is {sigma_ann_pct:.1f}%."
        )
        return "elevated", reason

    if sigma_ann_pct >= VOL_THRESHOLD_ELEVATED or abs(roc_7_pct) >= ROC_THRESHOLD_ELEVATED:
        reason = (
            f"ELEVATED RISK — Market entering unstable territory: 14-day volatility is {sigma_ann_pct:.1f}% "
            f"(threshold {VOL_THRESHOLD_ELEVATED}%) with 7-day ROC of {roc_7_pct:+.1f}%."
        )
        return "elevated", reason

    # 3. Calm Default
    reason = (
        f"CALM — Normal liquid market conditions: 14-day volatility is {sigma_ann_pct:.1f}% "
        f"and 7-day price trend is {roc_7_pct:+.1f}%. Standard chartering spreads apply."
    )
    return "calm", reason


def evaluate_market_risk(
    eval_date: DateType,
    route_id: Optional[int] = None,
    db: Optional[Session] = None,
    persist_flag: bool = False,
    freight_df: Optional[pd.DataFrame] = None,
) -> Dict:
    """
    Evaluate market risk for a given date and route.
    Optionally persists the active RiskFlag record to the database.
    """
    vol_stats = compute_market_volatility(
        eval_date=eval_date,
        freight_df=freight_df,
        db=db,
    )

    # Check for active disruption events around eval_date
    active_event: Optional[RiskEvent] = None
    if db is not None:
        window_start = eval_date - timedelta(days=7)
        window_end = eval_date + timedelta(days=14)
        query = db.query(RiskEvent).filter(
            RiskEvent.date >= window_start,
            RiskEvent.date <= window_end,
        )
        if route_id is not None:
            query = query.filter(
                (RiskEvent.affected_route_id == route_id) | (RiskEvent.affected_route_id.is_(None))
            )
        active_event = query.order_by(RiskEvent.severity_level.desc()).first()

    risk_level, reason = classify_risk_level(
        sigma_ann_pct=vol_stats["sigma_ann_pct"],
        roc_7_pct=vol_stats["roc_7_pct"],
        active_disruption=active_event,
    )

    # Risk Multiplier per blueprint Module D
    risk_mult = 1.50 if risk_level == "high" else (1.15 if risk_level == "elevated" else 1.00)

    # Persist to RiskFlags if requested and db is present
    flag_id = None
    if persist_flag and db is not None:
        existing = (
            db.query(RiskFlag)
            .filter(RiskFlag.date == eval_date, RiskFlag.route_id == route_id)
            .first()
        )
        if existing:
            existing.risk_level = risk_level
            existing.reason = reason
            existing.is_active = True
            db.commit()
            flag_id = existing.flag_id
        else:
            new_flag = RiskFlag(
                date=eval_date,
                route_id=route_id,
                risk_level=risk_level,
                reason=reason,
                is_active=True,
            )
            db.add(new_flag)
            db.commit()
            db.refresh(new_flag)
            flag_id = new_flag.flag_id

    return {
        "date": eval_date.isoformat(),
        "route_id": route_id,
        "risk_level": risk_level,  # 'calm' / 'elevated' / 'high'
        "risk_multiplier": risk_mult,  # 1.0 / 1.15 / 1.50
        "reason": reason,
        "metrics": {
            "current_freight_price": vol_stats["price"],
            "annualized_volatility_pct": vol_stats["sigma_ann_pct"],
            "roc_7_day_pct": vol_stats["roc_7_pct"],
            "daily_volatility_pct": vol_stats["daily_sigma_pct"],
        },
        "flag_id": flag_id,
        "active_disruption_event": (
            {
                "event_id": active_event.event_id,
                "event_type": active_event.event_type,
                "description": active_event.description,
                "severity_level": active_event.severity_level,
            }
            if active_event
            else None
        ),
    }


def replay_historical_risk_events(db: Session) -> pd.DataFrame:
    """
    Replay the curated RiskEvents dataset and verify whether the volatility-threshold
    rule and event-matching logic would have flagged each event concurrently or in advance.
    Returns a concrete backtest report DataFrame.
    """
    events: List[RiskEvent] = db.query(RiskEvent).order_by(RiskEvent.date.asc()).all()
    freight_df = load_freight_series_for_volatility(db=db)

    report_rows = []

    for event in events:
        event_date: DateType = cast(DateType, event.date)
        # Evaluate volatility at T-7 (advance lead check) and T (concurrent check)
        vol_advance = compute_market_volatility(eval_date=event_date - timedelta(days=7), freight_df=freight_df)
        vol_concurrent = compute_market_volatility(eval_date=event_date, freight_df=freight_df)

        # Evaluate risk radar status on event date
        eval_result = evaluate_market_risk(
            eval_date=event_date,
            route_id=cast(Optional[int], event.affected_route_id),
            db=db,
            persist_flag=False,
            freight_df=freight_df,
        )

        flagged_level = eval_result["risk_level"]
        caught = flagged_level in ("elevated", "high")

        # Determine detection timing
        if vol_advance["sigma_ann_pct"] >= VOL_THRESHOLD_ELEVATED or abs(vol_advance["roc_7_pct"]) >= ROC_THRESHOLD_ELEVATED:
            detection_timing = "IN ADVANCE (T-7d)"
        else:
            detection_timing = "CONCURRENT (T)"

        # Fetch route name if applicable
        route_name = "Market-wide"
        if event.affected_route_id:
            route_obj = db.query(Route).filter(Route.route_id == event.affected_route_id).first()
            if route_obj:
                route_name = f"Route #{route_obj.route_id}"

        report_rows.append({
            "event_id": event.event_id,
            "event_date": str(event_date),
            "event_type": event.event_type,
            "severity": event.severity_level,
            "route": route_name,
            "pre_vol_ann_pct": vol_advance["sigma_ann_pct"],
            "concurrent_vol_ann_pct": vol_concurrent["sigma_ann_pct"],
            "concurrent_roc_7_pct": vol_concurrent["roc_7_pct"],
            "flagged_level": flagged_level,
            "detection_timing": detection_timing,
            "caught": "YES" if caught else "NO",
            "historical_impact_pct": float(Decimal(str(event.historical_price_impact_pct))) if event.historical_price_impact_pct is not None else None,
            "description": event.description,
        })

    return pd.DataFrame(report_rows)
