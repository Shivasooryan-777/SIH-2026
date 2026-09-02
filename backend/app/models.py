"""
SQLAlchemy ORM Models
=====================
Strict 1:1 translation of the 15-table Entity Relationship Diagram in docs/blueprint.md Section 8.
No additional or omitted tables or columns.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Date,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    func,
)
from sqlalchemy.sql import expression
from backend.app.database import Base


# =============================================================================
# 8.1 Reference / Master Data Tables
# =============================================================================

class Port(Base):
    """
    Ports — Master list of all origin and destination ports in scope.
    """
    __tablename__ = "ports"

    port_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    country = Column(String(80), nullable=False)
    port_role = Column(String(20), nullable=False)  # 'origin' or 'destination'
    max_loa_m = Column(Numeric(6, 2), nullable=False)
    max_beam_m = Column(Numeric(6, 2), nullable=False)
    baseline_draft_m = Column(Numeric(5, 2), nullable=False)
    latitude = Column(Numeric(9, 6), nullable=True)
    longitude = Column(Numeric(9, 6), nullable=True)


class VesselType(Base):
    """
    VesselTypes — The four vessel size classes in scope with operating parameters.
    """
    __tablename__ = "vessel_types"

    vessel_type_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(30), nullable=False, unique=True)  # Handysize / Supramax / Panamax / Capesize
    min_dwt = Column(Integer, nullable=False)
    max_dwt = Column(Integer, nullable=False)
    required_draft_m = Column(Numeric(5, 2), nullable=False)
    typical_loa_m = Column(Numeric(6, 2), nullable=False)
    typical_beam_m = Column(Numeric(6, 2), nullable=False)
    standard_speed_knots = Column(Numeric(4, 1), nullable=False)
    fuel_curve_coef = Column(Numeric(8, 4), nullable=False)


class Route(Base):
    """
    Routes — Defined origin-to-destination shipping lanes.
    """
    __tablename__ = "routes"

    route_id = Column(Integer, primary_key=True, autoincrement=True)
    origin_port_id = Column(Integer, ForeignKey("ports.port_id"), nullable=False)
    destination_port_id = Column(Integer, ForeignKey("ports.port_id"), nullable=False)
    distance_nm = Column(Integer, nullable=False)
    typical_transit_days = Column(Numeric(4, 1), nullable=False)


# =============================================================================
# 8.2 Ingested Time-Series / Reference Data Tables
# =============================================================================

class FreightRateData(Base):
    """
    FreightRateData — Daily freight rate proxy values per vessel class.
    """
    __tablename__ = "freight_rate_data"

    rate_id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    vessel_type_id = Column(Integer, ForeignKey("vessel_types.vessel_type_id"), nullable=False)
    index_type = Column(String(30), nullable=False)  # e.g., 'BDRY_proxy'
    value_usd_per_day = Column(Numeric(10, 2), nullable=False)
    source = Column(String(50), nullable=False)


class MacroIndicator(Base):
    """
    MacroIndicators — Daily macro/leading-indicator series used as model features.
    """
    __tablename__ = "macro_indicators"

    indicator_id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    indicator_type = Column(String(30), nullable=False)  # 'brent_crude' / 'coal_futures' / 'usd_inr' / 'iron_ore'
    value = Column(Numeric(12, 4), nullable=False)


class PortDraftAdvisory(Base):
    """
    PortDraftAdvisory — Date-specific overrides to a port's available draft.
    """
    __tablename__ = "port_draft_advisory"

    advisory_id = Column(Integer, primary_key=True, autoincrement=True)
    port_id = Column(Integer, ForeignKey("ports.port_id"), nullable=False)
    date = Column(Date, nullable=False)
    available_draft_m = Column(Numeric(5, 2), nullable=False)
    season_tag = Column(String(20), nullable=True)  # e.g., 'monsoon', 'post-dredging'


class RiskEvent(Base):
    """
    RiskEvents — Curated historical disruption dataset used to validate Risk Radar.
    """
    __tablename__ = "risk_events"

    event_id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    event_type = Column(String(40), nullable=False)  # 'canal_blockage' / 'cyclone' / 'geopolitical'
    description = Column(Text, nullable=False)
    affected_route_id = Column(Integer, ForeignKey("routes.route_id"), nullable=True)
    severity_level = Column(String(10), nullable=False)  # 'low' / 'medium' / 'high'
    historical_price_impact_pct = Column(Numeric(6, 2), nullable=True)


# =============================================================================
# 8.3 Workflow / Request-Driven Tables
# =============================================================================

class CargoRequest(Base):
    """
    CargoRequests — One row per query submitted through the dashboard.
    """
    __tablename__ = "cargo_requests"

    request_id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    cargo_type = Column(String(40), nullable=False)  # e.g., 'coking_coal', 'iron_ore'
    cargo_volume_tons = Column(Integer, nullable=False)
    origin_port_id = Column(Integer, ForeignKey("ports.port_id"), nullable=False)
    destination_port_id = Column(Integer, ForeignKey("ports.port_id"), nullable=False)
    desired_timeframe_days = Column(Integer, nullable=False)
    desired_contract_pref = Column(String(10), nullable=True)  # 'spot' / 'period' / 'no_preference'


class ForecastResult(Base):
    """
    ForecastResults — Output of Module A for a given request and vessel type.
    """
    __tablename__ = "forecast_results"

    forecast_id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(Integer, ForeignKey("cargo_requests.request_id"), nullable=False)
    generated_at = Column(DateTime, nullable=False, server_default=func.now())
    vessel_type_id = Column(Integer, ForeignKey("vessel_types.vessel_type_id"), nullable=False)
    p10_price = Column(Numeric(10, 2), nullable=False)
    p50_price = Column(Numeric(10, 2), nullable=False)
    p90_price = Column(Numeric(10, 2), nullable=False)
    model_version = Column(String(20), nullable=False)


class ShapExplanation(Base):
    """
    ShapExplanations — Feature-attribution rows explaining a ForecastResult entry.
    """
    __tablename__ = "shap_explanations"

    explanation_id = Column(Integer, primary_key=True, autoincrement=True)
    forecast_id = Column(Integer, ForeignKey("forecast_results.forecast_id"), nullable=False)
    feature_name = Column(String(50), nullable=False)
    contribution_pct = Column(Numeric(5, 2), nullable=False)
    direction = Column(String(10), nullable=False)  # 'upward' / 'downward'


class RiskFlag(Base):
    """
    RiskFlags — Output of Module C — active or historical risk flags per route.
    """
    __tablename__ = "risk_flags"

    flag_id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    route_id = Column(Integer, ForeignKey("routes.route_id"), nullable=True)
    risk_level = Column(String(10), nullable=False)  # 'calm' / 'elevated' / 'high'
    reason = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default=expression.true())


# =============================================================================
# 8.4 Recommendation & Action-Logging Tables
# =============================================================================

class DecisionRecommendation(Base):
    """
    DecisionRecommendations — Output of Module D — core fix-now-vs-wait recommendation.
    """
    __tablename__ = "decision_recommendations"

    decision_id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(Integer, ForeignKey("cargo_requests.request_id"), nullable=False)
    recommended_vessel_type_id = Column(Integer, ForeignKey("vessel_types.vessel_type_id"), nullable=False)
    recommended_action = Column(String(10), nullable=False)  # 'fix_now' / 'wait'
    expected_price = Column(Numeric(10, 2), nullable=False)
    expected_savings_usd = Column(Numeric(10, 2), nullable=False)
    generated_at = Column(DateTime, nullable=False, server_default=func.now())


class IdleTimeAnalysis(Base):
    """
    IdleTimeAnalysis — Output of Module E1 — spot-vs-period contract structuring.
    """
    __tablename__ = "idle_time_analysis"

    analysis_id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(Integer, ForeignKey("cargo_requests.request_id"), nullable=False)
    recommended_contract_type = Column(String(10), nullable=False)  # 'spot' / 'period'
    forecasted_trough_start = Column(Date, nullable=True)
    forecasted_trough_end = Column(Date, nullable=True)
    estimated_cost_saved_usd = Column(Numeric(10, 2), nullable=True)


class SpeedOptimizationLog(Base):
    """
    SpeedOptimizationLog — Output of Module E2 — JIT speed/fuel advisory in transit.
    """
    __tablename__ = "speed_optimization_log"

    speed_id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(Integer, ForeignKey("cargo_requests.request_id"), nullable=False)
    route_id = Column(Integer, ForeignKey("routes.route_id"), nullable=False)
    standard_speed_knots = Column(Numeric(4, 1), nullable=False)
    recommended_speed_knots = Column(Numeric(4, 1), nullable=False)
    port_congestion_hours = Column(Numeric(6, 1), nullable=False)
    fuel_saved_tons = Column(Numeric(8, 2), nullable=False)
    co2_reduced_kg = Column(Numeric(10, 2), nullable=False)


class ActionedDecision(Base):
    """
    ActionedDecisions — Anonymous log of recommendations the user marked as acted upon.
    """
    __tablename__ = "actioned_decisions"

    action_id = Column(Integer, primary_key=True, autoincrement=True)
    decision_id = Column(Integer, ForeignKey("decision_recommendations.decision_id"), nullable=False)
    actioned_at = Column(DateTime, nullable=False, server_default=func.now())
    note = Column(Text, nullable=True)
