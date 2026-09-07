/**
 * Data types matching backend schema
 */

export type int = number;

export interface Port {
  port_id: int;
  name: string;
  country: string;
  port_role: 'origin' | 'destination';
  max_loa_m: number;
  max_beam_m: number;
  baseline_draft_m: number;
  latitude?: number | null;
  longitude?: number | null;
}

export interface VesselType {
  vessel_type_id: int;
  name: string;
  min_dwt: int;
  max_dwt: int;
  required_draft_m: number;
  typical_loa_m: number;
  typical_beam_m: number;
  standard_speed_knots: number;
  fuel_curve_coef: number;
}

export interface Route {
  route_id: int;
  origin_port_id: int;
  origin_port_name: string;
  origin_country: string;
  destination_port_id: int;
  destination_port_name: string;
  destination_country: string;
  distance_nm: int;
  typical_transit_days: number;
}

export interface ActiveRiskFlag {
  flag_id: int;
  date: string;
  route_id: int | null;
  corridor: string;
  risk_level: 'calm' | 'elevated' | 'high' | string;
  reason: string;
  is_active: boolean;
}

export interface MarketWatchResponse {
  as_of_date: string;
  overall_sentiment: 'calm' | 'elevated' | 'high' | string;
  summary_reason: string;
  active_flags_count: int;
  active_flags: ActiveRiskFlag[];
  macro_metrics: Record<string, unknown>;
}

export interface DecisionEvaluationRequest {
  cargo_type?: string;
  cargo_volume_tons: int;
  origin_port_id: int;
  destination_port_id: int;
  desired_timeframe_days: int;
  desired_contract_pref?: 'spot' | 'period' | 'no_preference';
  date?: string;
  vessel_in_transit?: boolean;
  distance_remaining_nm?: number;
}

export interface ForecastBandPoint {
  horizon_days: number;
  target_date?: string;
  p10_price: number;
  p50_price: number;
  p90_price: number;
  spread: number;
}

export interface ShapItem {
  feature_name: string;
  contribution_pct: number;
  direction: 'upward' | 'downward';
}

export interface HorizonEvaluation {
  horizon_days: number;
  target_date?: string;
  f_wait: number;
  spread: number;
  gross_price_change: number;
  risk_premium: number;
  expected_value_of_waiting: number;
}

export interface VesselPortCheck {
  vessel_type_id: number;
  name: string;
  min_dwt: number;
  max_dwt: number;
  required_draft_m: number;
  typical_loa_m: number;
  typical_beam_m: number;
  is_compatible: boolean;
  draft_margin_m: number;
  loa_margin_m: number;
  beam_margin_m: number;
  cargo_capacity_status?: string;
}

export interface PortCompatibilityData {
  port_id: number;
  port_name: string;
  port_role: string;
  country: string;
  date: string;
  baseline_draft_m: number;
  effective_draft_m: number;
  seasonal_factor: number;
  ranked_compatible_vessels: VesselPortCheck[];
  incompatible_vessels: VesselPortCheck[];
}

export interface SpotVsPeriodData {
  recommended_contract_type: 'spot' | 'period' | string;
  trough_detected: boolean;
  trough_window_days_required?: number;
  contiguous_trough_days_found?: number;
  p20_threshold_usd?: number;
  trailing_median_usd?: number;
  forecasted_trough_start?: string | null;
  forecasted_trough_end?: string | null;
  estimated_cost_saved_usd: number;
  reason: string;
}

export interface SpeedAndFuelAdvisoryData {
  applicable: boolean;
  standard_speed_knots?: number;
  recommended_speed_knots?: number;
  port_congestion_hours?: number;
  fuel_saved_tons?: number;
  co2_reduced_kg?: number;
  cost_saved_usd?: number;
  bunker_saved_usd?: number;
  reason?: string;
}

export interface DecisionEvaluationResponse {
  decision_id: number;
  request_id: number;
  recommended_vessel_type_id: number;
  recommended_vessel_name: string;
  recommended_action: string; // 'fix_now' | 'wait'
  recommended_window_days: number;
  expected_price: number;
  expected_savings_usd: number;
  risk_level: string;
  risk_multiplier: number;
  reason: string;
  generated_at: string;
  port_compatibility?: PortCompatibilityData;
  horizon_evaluations?: HorizonEvaluation[];
  idle_contract?: {
    request_id?: number;
    eval_date?: string;
    spot_vs_period?: SpotVsPeriodData;
    speed_and_fuel_advisory?: SpeedAndFuelAdvisoryData;
  };
  forecast_curve?: ForecastBandPoint[];
  shap_explanations?: ShapItem[];
}

export interface ActionResponse {
  status: string;
  action_id: number;
  decision_id: number;
  actioned_at: string;
  note?: string | null;
}

