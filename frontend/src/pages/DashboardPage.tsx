import React, { useState } from 'react';
import { TopBar } from '../components/TopBar';
import { CargoProcurementForm } from '../components/CargoProcurementForm';
import { EmptyState } from '../components/dashboard/EmptyState';
import { LoadingSkeleton } from '../components/dashboard/LoadingSkeleton';
import { ErrorState } from '../components/dashboard/ErrorState';
import { QuantileBandChart } from '../components/dashboard/QuantileBandChart';
import { ShapBarChart } from '../components/dashboard/ShapBarChart';
import { ActionConfirmButton } from '../components/dashboard/ActionConfirmButton';
import { TransparencyDrawer } from '../components/dashboard/TransparencyDrawer';
import type { DecisionEvaluationRequest, DecisionEvaluationResponse } from '../api/types';
import { evaluateDecision } from '../api/client';
import { CheckCircle2, Anchor, Clock, Info } from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [decisionResult, setDecisionResult] = useState<DecisionEvaluationResponse | null>(null);
  const [lastPayload, setLastPayload] = useState<DecisionEvaluationRequest | null>(null);
  const [isTransparencyOpen, setIsTransparencyOpen] = useState<boolean>(false);

  const handleEvaluate = async (payload: DecisionEvaluationRequest) => {
    setIsLoading(true);
    setError(null);
    setLastPayload(payload);

    try {
      const data = await evaluateDecision(payload);
      setDecisionResult(data);
    } catch (err: any) {
      setError(err.message || 'Failed to evaluate chartering decision');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRetry = () => {
    if (lastPayload) {
      handleEvaluate(lastPayload);
    }
  };

  return (
    <div className="min-h-screen bg-[#09090B] text-text-primary flex flex-col selection:bg-accent/25 selection:text-accent-glow">
      {/* Top Bar with Live DB Health and Always-On Market Watch Ticker */}
      <TopBar onOpenTransparency={() => setIsTransparencyOpen(true)} />

      {/* Main Dashboard Layout */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Cargo Procurement Form (lg:col-span-4) */}
          <div className="lg:col-span-4 w-full">
            <CargoProcurementForm onSubmit={handleEvaluate} isLoading={isLoading} />
          </div>

          {/* Right Column: Decision Cockpit Display (lg:col-span-8) */}
          <div className="lg:col-span-8 w-full">
            {isLoading && <LoadingSkeleton />}

            {!isLoading && error && (
              <ErrorState error={error} onRetry={handleRetry} />
            )}

            {!isLoading && !error && !decisionResult && (
              <EmptyState />
            )}

            {!isLoading && !error && decisionResult && (
              <div className="space-y-6">
                {/* Decision Hero Card — Exclusive soft accent-glow shadow per design system */}
                {(() => {
                  const isFixNow = (decisionResult.recommended_action || '').toLowerCase().includes('fix');
                  const actionColor = isFixNow ? '#22A97A' : '#E8A33D';
                  const expectedPrice = Number(decisionResult.expected_price || 0);
                  const expectedSavings = Number(decisionResult.expected_savings_usd || 0);
                  const windowDays = decisionResult.recommended_window_days ?? 0;
                  const portComp = decisionResult.port_compatibility;
                  const spotVsPeriod = decisionResult.idle_contract?.spot_vs_period;
                  const speedAdvisory = decisionResult.idle_contract?.speed_and_fuel_advisory;

                  return (
                    <>
                      <div className="rounded-2xl bg-[#131316] border border-[#26262B] p-6 shadow-accent-glow relative overflow-hidden">
                        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                          <div className="flex items-center gap-2.5">
                            <span
                              className="px-3.5 py-1 rounded-full text-xs font-mono font-bold uppercase tracking-wider"
                              style={{
                                backgroundColor: `${actionColor}20`,
                                color: actionColor,
                                border: `1px solid ${actionColor}40`,
                              }}
                            >
                              ● {isFixNow ? 'FIX NOW' : 'WAIT'}
                            </span>
                            <span className="text-xs font-mono text-text-tertiary">
                              Window: {windowDays > 0 ? `${windowDays}d horizon` : 'Immediate Execution'}
                            </span>
                            <span className="text-xs font-mono text-text-tertiary">
                              Risk: <span className="uppercase" style={{ color: actionColor }}>{decisionResult.risk_level || 'calm'}</span>
                            </span>
                          </div>

                          <div className="flex flex-wrap items-center gap-3">
                            <ActionConfirmButton decisionId={decisionResult.decision_id} />
                            <div className="flex items-center gap-1.5 text-xs font-mono text-[#22A97A]">
                              <CheckCircle2 className="w-4 h-4" />
                              <span>Live Evaluation Complete</span>
                            </div>
                          </div>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
                          <div className="p-3.5 rounded-2xl bg-[#09090B] border border-[#26262B] flex flex-col justify-between">
                            <div>
                              <div className="text-[11px] text-text-tertiary uppercase font-medium">
                                Expected Daily Rate
                              </div>
                              <div className="text-xl font-bold font-mono text-text-primary mt-1">
                                ${expectedPrice.toLocaleString('en-US', {
                                  minimumFractionDigits: 2,
                                  maximumFractionDigits: 2,
                                })}
                                <span className="text-xs font-normal text-text-tertiary">/day</span>
                              </div>
                            </div>
                            <div className="text-[10px] text-text-tertiary mt-2 pt-2 border-t border-[#26262B]/80 leading-snug flex items-start gap-1.5">
                              <Info className="w-3 h-3 text-accent shrink-0 mt-0.5" />
                              <span>General dry-bulk freight index (BDRY ETF proxy) — not a literal vessel charter day-rate.</span>
                            </div>
                          </div>

                          <div className="p-3.5 rounded-2xl bg-[#09090B] border border-[#26262B] flex flex-col justify-between">
                            <div>
                              <div className="text-[11px] text-text-tertiary uppercase font-medium">
                                Expected Net Savings
                              </div>
                              <div className="text-xl font-bold font-mono text-[#22A97A] mt-1">
                                ${expectedSavings.toLocaleString('en-US', {
                                  minimumFractionDigits: 2,
                                  maximumFractionDigits: 2,
                                })}
                                <span className="text-xs font-normal text-text-tertiary ml-1">
                                  /day
                                </span>
                              </div>
                            </div>
                            <div className="text-[10px] text-text-tertiary mt-2 pt-2 border-t border-[#26262B]/80 leading-snug flex items-start gap-1.5">
                              <Info className="w-3 h-3 text-accent shrink-0 mt-0.5" />
                              <span>General dry-bulk freight index (BDRY ETF proxy) — not a literal vessel charter day-rate.</span>
                            </div>
                          </div>

                          <div className="p-3.5 rounded-2xl bg-[#09090B] border border-[#26262B] flex flex-col justify-between">
                            <div>
                              <div className="text-[11px] text-text-tertiary uppercase font-medium">
                                Recommended Vessel
                              </div>
                              <div className="text-xl font-bold font-mono text-accent mt-1 truncate">
                                {decisionResult.recommended_vessel_name || 'Panamax'}
                              </div>
                            </div>
                            <div className="text-[10px] text-text-tertiary mt-2 pt-2 border-t border-[#26262B]/80 leading-snug">
                              Determined by Module B physical port draft/LOA compatibility.
                            </div>
                          </div>
                        </div>

                        {/* Operational Rationale */}
                        <div className="p-3.5 rounded-2xl bg-[#09090B] border border-[#26262B]">
                          <div className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider mb-1">
                            Engine Rationale &amp; Optimization Basis
                          </div>
                          <p className="text-xs text-text-primary leading-relaxed">
                            {decisionResult.reason}
                          </p>
                        </div>
                      </div>

                      {/* Visual Analytics: Quantile Band Forecast & SHAP Attributions */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                        <QuantileBandChart
                          forecastCurve={decisionResult.forecast_curve}
                          currentSpotPrice={expectedPrice}
                        />
                        <ShapBarChart
                          shapExplanations={decisionResult.shap_explanations}
                        />
                      </div>

                      {/* Ports & Compatibility Preview (Module B) */}
                      {portComp && (
                        <div className="p-5 rounded-2xl bg-[#131316] border border-[#26262B]">
                          <div className="flex items-center justify-between mb-3 pb-2 border-b border-[#26262B]">
                            <span className="text-xs font-semibold text-text-primary flex items-center gap-2">
                              <Anchor className="w-4 h-4 text-accent" />
                              Destination Compatibility ({portComp.port_name})
                            </span>
                            <span className="text-[11px] font-mono text-text-tertiary">
                              Effective Draft: {Number(portComp.effective_draft_m || 0).toFixed(1)}m
                            </span>
                          </div>

                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
                            {(portComp.ranked_compatible_vessels || []).map((v) => (
                              <div
                                key={v.vessel_type_id}
                                className="p-2.5 rounded-xl border bg-[#09090B] border-[#22A97A]/40 text-[#22A97A]"
                              >
                                <div className="font-semibold text-text-primary">{v.name}</div>
                                <div className="text-[10px] mt-0.5 text-[#22A97A]">COMPATIBLE</div>
                                <div className="text-[10px] text-text-tertiary mt-0.5">
                                  Margin: +{Number(v.draft_margin_m || 0).toFixed(1)}m
                                </div>
                              </div>
                            ))}
                            {(portComp.incompatible_vessels || []).map((v) => (
                              <div
                                key={v.vessel_type_id}
                                className="p-2.5 rounded-xl border bg-[#09090B] border-[#26262B] text-text-tertiary opacity-60"
                              >
                                <div className="font-semibold text-text-primary">{v.name}</div>
                                <div className="text-[10px] mt-0.5 text-[#E4574C]">RESTRICTED</div>
                                <div className="text-[10px] text-text-tertiary mt-0.5">Draft limited</div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Idle-Time / Contract Structuring Preview (Module E1) */}
                      {spotVsPeriod && (
                        <div className="p-5 rounded-2xl bg-[#131316] border border-[#26262B]">
                          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                            <span className="text-xs font-semibold text-text-primary flex items-center gap-2">
                              <Clock className="w-4 h-4 text-[#E8A33D]" />
                              Contract Structuring &amp; Trough Advisory (Module E1)
                            </span>
                            <div className="flex items-center gap-2">
                              {spotVsPeriod.p20_threshold_usd !== undefined && (
                                <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-[#09090B] border border-[#26262B] text-text-secondary">
                                  Trough Threshold: <span className="font-bold text-text-primary">${Number(spotVsPeriod.p20_threshold_usd).toFixed(2)}/day</span>
                                </span>
                              )}
                              <span className="text-xs font-mono font-bold uppercase text-accent px-2.5 py-1 rounded-full bg-[#09090B] border border-[#26262B]">
                                {spotVsPeriod.recommended_contract_type} Charter
                              </span>
                            </div>
                          </div>
                          <p className="text-xs text-text-secondary leading-relaxed mb-3">
                            {spotVsPeriod.reason}
                          </p>
                          <div className="text-[10px] text-text-tertiary pt-2 border-t border-[#26262B]/80 leading-snug flex items-start gap-1.5">
                            <Info className="w-3 h-3 text-accent shrink-0 mt-0.5" />
                            <span>General dry-bulk freight index (BDRY ETF proxy) — not a literal vessel charter day-rate.</span>
                          </div>
                        </div>
                      )}

                      {/* Speed & Decarbonization Preview (Module E2, if in transit) */}
                      {speedAdvisory && speedAdvisory.applicable && (
                        <div className="p-5 rounded-2xl bg-[#131316] border border-[#26262B]">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-xs font-semibold text-text-primary flex items-center gap-2">
                              <Anchor className="w-4 h-4 text-[#22A97A]" />
                              JIT Speed &amp; Marine Decarbonization (Module E2)
                            </span>
                            <span className="text-xs font-mono text-[#22A97A]">
                              Speed: {speedAdvisory.recommended_speed_knots} kts (std {speedAdvisory.standard_speed_knots} kts)
                            </span>
                          </div>
                          <div className="grid grid-cols-3 gap-3 text-xs font-mono mt-3">
                            <div className="p-2.5 rounded-xl bg-[#09090B] border border-[#26262B]">
                              <span className="text-[10px] text-text-tertiary block">FUEL SAVED</span>
                              <span className="text-text-primary font-bold">{Number(speedAdvisory.fuel_saved_tons || 0).toFixed(1)} MT</span>
                            </div>
                            <div className="p-2.5 rounded-xl bg-[#09090B] border border-[#26262B]">
                              <span className="text-[10px] text-text-tertiary block">CO2 REDUCED</span>
                              <span className="text-text-primary font-bold">{Number(speedAdvisory.co2_reduced_kg || 0).toLocaleString()} kg</span>
                            </div>
                            <div className="p-2.5 rounded-xl bg-[#09090B] border border-[#26262B]">
                              <span className="text-[10px] text-text-tertiary block">BUNKER SAVED</span>
                              <span className="text-[#22A97A] font-bold">${Number(speedAdvisory.cost_saved_usd || 0).toLocaleString()}</span>
                            </div>
                          </div>
                        </div>
                      )}
                    </>
                  );
                })()}
              </div>
            )}
          </div>
        </div>
      </main>
      <TransparencyDrawer
        isOpen={isTransparencyOpen}
        onClose={() => setIsTransparencyOpen(false)}
      />
    </div>
  );
};
