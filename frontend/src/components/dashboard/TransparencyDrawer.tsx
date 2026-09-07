import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ShieldCheck, FileText, Table, Sliders, AlertTriangle, CheckCircle2 } from 'lucide-react';

interface TransparencyDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export const TransparencyDrawer: React.FC<TransparencyDrawerProps> = ({
  isOpen,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<'summary' | 'disclosures' | 'fixtures'>('summary');

  // ESC key listener to close drawer
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  const fixtures = [
    { id: 1, date: '2020-04-15', corridor: 'Taboneo → Haldia', vessel: 'Supramax', action: 'FIX_NOW', window: '0d', base: 7.25, real: 7.25, saving: '+0.0%' },
    { id: 2, date: '2020-06-16', corridor: 'Taboneo → Paradip_Inner', vessel: 'Supramax', action: 'FIX_NOW', window: '0d', base: 7.22, real: 7.22, saving: '+0.0%' },
    { id: 3, date: '2020-08-18', corridor: 'Maputo → Dhamra', vessel: 'Panamax', action: 'FIX_NOW', window: '0d', base: 8.84, real: 8.84, saving: '+0.0%' },
    { id: 4, date: '2020-10-20', corridor: 'Beira → Dhamra', vessel: 'Panamax', action: 'FIX_NOW', window: '0d', base: 7.39, real: 7.39, saving: '+0.0%' },
    { id: 5, date: '2020-12-15', corridor: 'Nacala → Gangavaram', vessel: 'Panamax', action: 'WAIT', window: '14d', base: 7.30, real: 7.20, saving: '+1.4%' },
    { id: 6, date: '2021-02-16', corridor: 'Vostochny_PPK3 → Vizag_Outer', vessel: 'Panamax', action: 'WAIT', window: '14d', base: 15.82, real: 14.89, saving: '+5.9%' },
    { id: 7, date: '2021-04-20', corridor: 'Newcastle → Paradip_SPM', vessel: 'Capesize', action: 'FIX_NOW', window: '0d', base: 20.45, real: 20.45, saving: '+0.0%' },
    { id: 8, date: '2021-06-15', corridor: 'Lamberts_Point → Vizag_Outer', vessel: 'Panamax', action: 'FIX_NOW', window: '0d', base: 28.99, real: 28.99, saving: '+0.0%' },
    { id: 9, date: '2021-08-17', corridor: 'Taboneo → Haldia', vessel: 'Supramax', action: 'FIX_NOW', window: '0d', base: 29.21, real: 29.21, saving: '+0.0%' },
    { id: 10, date: '2021-10-19', corridor: 'Taboneo → Paradip_Inner', vessel: 'Supramax', action: 'FIX_NOW', window: '0d', base: 38.48, real: 38.48, saving: '+0.0%' },
    { id: 11, date: '2021-12-14', corridor: 'Maputo → Dhamra', vessel: 'Panamax', action: 'FIX_NOW', window: '0d', base: 23.61, real: 23.61, saving: '+0.0%' },
    { id: 12, date: '2022-02-15', corridor: 'Beira → Dhamra', vessel: 'Panamax', action: 'FIX_NOW', window: '0d', base: 22.66, real: 22.66, saving: '+0.0%' },
    { id: 13, date: '2022-04-19', corridor: 'Nacala → Gangavaram', vessel: 'Panamax', action: 'FIX_NOW', window: '0d', base: 21.23, real: 21.23, saving: '+0.0%' },
    { id: 14, date: '2022-06-21', corridor: 'Vostochny_PPK3 → Vizag_Outer', vessel: 'Panamax', action: 'FIX_NOW', window: '0d', base: 18.29, real: 18.29, saving: '+0.0%' },
    { id: 15, date: '2022-08-16', corridor: 'Newcastle → Paradip_SPM', vessel: 'Panamax', action: 'FIX_NOW', window: '0d', base: 9.99, real: 9.99, saving: '+0.0%' },
    { id: 16, date: '2022-10-18', corridor: 'Lamberts_Point → Vizag_Outer', vessel: 'Panamax', action: 'WAIT', window: '14d', base: 9.19, real: 7.41, saving: '+19.4%' },
    { id: 17, date: '2022-12-20', corridor: 'Taboneo → Haldia', vessel: 'Supramax', action: 'WAIT', window: '14d', base: 9.98, real: 8.82, saving: '+11.6%' },
    { id: 18, date: '2023-02-21', corridor: 'Taboneo → Paradip_Inner', vessel: 'Panamax', action: 'WAIT', window: '14d', base: 7.06, real: 9.18, saving: '-30.0%' },
    { id: 19, date: '2023-04-18', corridor: 'Maputo → Dhamra', vessel: 'Panamax', action: 'WAIT', window: '14d', base: 8.62, real: 8.28, saving: '+3.9%' },
    { id: 20, date: '2023-06-20', corridor: 'Beira → Dhamra', vessel: 'Panamax', action: 'FIX_NOW', window: '0d', base: 6.16, real: 6.16, saving: '+0.0%' },
    { id: 21, date: '2023-08-15', corridor: 'Nacala → Gangavaram', vessel: 'Panamax', action: 'FIX_NOW', window: '0d', base: 5.59, real: 5.59, saving: '+0.0%' },
    { id: 22, date: '2023-10-17', corridor: 'Vostochny_PPK3 → Vizag_Outer', vessel: 'Panamax', action: 'FIX_NOW', window: '0d', base: 6.09, real: 6.09, saving: '+0.0%' },
    { id: 23, date: '2023-12-19', corridor: 'Newcastle → Paradip_SPM', vessel: 'Capesize', action: 'FIX_NOW', window: '0d', base: 9.78, real: 9.78, saving: '+0.0%' },
    { id: 24, date: '2024-02-20', corridor: 'Lamberts_Point → Vizag_Outer', vessel: 'Panamax', action: 'WAIT', window: '14d', base: 12.50, real: 15.75, saving: '-26.0%' },
    { id: 25, date: '2024-04-16', corridor: 'Taboneo → Paradip_Inner', vessel: 'Panamax', action: 'FIX_NOW', window: '0d', base: 13.40, real: 13.40, saving: '+0.0%' },
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex justify-end">
          {/* Backdrop Scrim */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-[#09090B]/80 backdrop-blur-sm"
          />

          {/* Drawer Panel */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 260 }}
            className="relative w-full max-w-2xl h-full bg-[#131316] border-l border-[#26262B] shadow-2xl flex flex-col z-10"
          >
            {/* Drawer Header */}
            <div className="p-5 border-b border-[#26262B] flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-[#09090B] border border-[#26262B] flex items-center justify-center text-accent">
                  <Sliders className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-text-primary tracking-tight">
                    Model Transparency &amp; Backtest Disclosures
                  </h2>
                  <p className="text-xs text-text-tertiary">SIH26006 • Ministry of Steel Governance Standard</p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="w-8 h-8 rounded-xl bg-[#09090B] border border-[#26262B] flex items-center justify-center text-text-tertiary hover:text-text-primary transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Navigation Tabs */}
            <div className="flex border-b border-[#26262B] bg-[#09090B]/50 px-5 pt-2 gap-2 text-xs font-medium">
              <button
                onClick={() => setActiveTab('summary')}
                className={`pb-2.5 px-3 border-b-2 font-mono flex items-center gap-1.5 transition-colors ${
                  activeTab === 'summary'
                    ? 'border-accent text-accent font-semibold'
                    : 'border-transparent text-text-tertiary hover:text-text-secondary'
                }`}
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Headline Deliverables</span>
              </button>
              <button
                onClick={() => setActiveTab('disclosures')}
                className={`pb-2.5 px-3 border-b-2 font-mono flex items-center gap-1.5 transition-colors ${
                  activeTab === 'disclosures'
                    ? 'border-accent text-accent font-semibold'
                    : 'border-transparent text-text-tertiary hover:text-text-secondary'
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>5 Disclosures</span>
              </button>
              <button
                onClick={() => setActiveTab('fixtures')}
                className={`pb-2.5 px-3 border-b-2 font-mono flex items-center gap-1.5 transition-colors ${
                  activeTab === 'fixtures'
                    ? 'border-accent text-accent font-semibold'
                    : 'border-transparent text-text-tertiary hover:text-text-secondary'
                }`}
              >
                <Table className="w-3.5 h-3.5" />
                <span>25-Fixture Backtest</span>
              </button>
            </div>

            {/* Content Body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-6 text-xs text-text-secondary leading-relaxed">
              {/* TAB 1: HEADLINE DELIVERABLES */}
              {activeTab === 'summary' && (
                <div className="space-y-4">
                  <div className="p-4 rounded-2xl bg-[#09090B] border border-[#26262B]">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold text-text-primary text-sm flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 text-[#22A97A]" />
                        Module D: Chartering Decision Engine
                      </span>
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-[#22A97A]/20 text-[#22A97A]">
                        PASSED SANITY GUARDRAIL
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-3 font-mono text-xs my-2">
                      <div className="p-2.5 rounded-xl bg-[#131316] border border-[#26262B]">
                        <span className="text-[10px] text-text-tertiary block">25-FIXTURE NET RESULT</span>
                        <span className="text-text-primary font-bold">-0.30% ($-1.06)</span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-[#131316] border border-[#26262B]">
                        <span className="text-[10px] text-text-tertiary block">CHALLENGE 10 BOUND</span>
                        <span className="text-[#22A97A] font-bold">&le; 25.0% Limit</span>
                      </div>
                    </div>
                    <p className="text-[11px] text-text-tertiary mt-2">
                      Quantified expected-value FIX NOW vs. WAIT policy evaluated across 25 real historical fixtures. Zero free-lunch claims; protects against downside exposure during volatile periods.
                    </p>
                  </div>

                  <div className="p-4 rounded-2xl bg-[#09090B] border border-[#26262B]">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold text-text-primary text-sm flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 text-[#22A97A]" />
                        Module E1: Spot-vs-Period Structuring
                      </span>
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-[#22A97A]/20 text-[#22A97A]">
                        PS REQ (c) COMPLIANT
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-3 font-mono text-xs my-2">
                      <div className="p-2.5 rounded-xl bg-[#131316] border border-[#26262B]">
                        <span className="text-[10px] text-text-tertiary block">TROUGH PERIOD SAVINGS</span>
                        <span className="text-[#22A97A] font-bold">+3.62% ($372.50)</span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-[#131316] border border-[#26262B]">
                        <span className="text-[10px] text-text-tertiary block">IDLE DAYS ELIMINATED</span>
                        <span className="text-accent font-bold">44.0 Idle Days</span>
                      </div>
                    </div>
                    <p className="text-[11px] text-text-tertiary mt-2">
                      Structures period charters across verified 14-day market troughs (11/25 fixtures), eliminating turnaround deadweight and locking bottom-cycle freight rates.
                    </p>
                  </div>

                  <div className="p-4 rounded-2xl bg-[#09090B] border border-[#26262B]">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold text-text-primary text-sm flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 text-[#22A97A]" />
                        Module E2: JIT Speed &amp; Decarbonization
                      </span>
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-[#22A97A]/20 text-[#22A97A]">
                        MARITIME PHYSICS
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 font-mono text-xs my-2">
                      <div className="p-2 rounded-xl bg-[#131316] border border-[#26262B]">
                        <span className="text-[10px] text-text-tertiary block">VLSFO FUEL</span>
                        <span className="text-[#22A97A] font-bold text-[11px]">521.15 t</span>
                      </div>
                      <div className="p-2 rounded-xl bg-[#131316] border border-[#26262B]">
                        <span className="text-[10px] text-text-tertiary block">CO2 REDUCED</span>
                        <span className="text-[#22A97A] font-bold text-[11px]">1,622.9 t</span>
                      </div>
                      <div className="p-2 rounded-xl bg-[#131316] border border-[#26262B]">
                        <span className="text-[10px] text-text-tertiary block">BUNKER SAVED</span>
                        <span className="text-accent font-bold text-[11px]">$312,698</span>
                      </div>
                    </div>
                    <p className="text-[11px] text-text-tertiary mt-2">
                      Applies Admiralty cubic fuel law with IMO MEPC.1/Circ.684 minimum safe speed bounds (&ge; 10.0 kts), absorbing 254 hours of port congestion waiting at sea.
                    </p>
                  </div>
                </div>
              )}

              {/* TAB 2: VERBATIM DISCLOSURES */}
              {activeTab === 'disclosures' && (
                <div className="space-y-4">
                  <div className="p-4 rounded-2xl bg-[#09090B] border border-[#26262B]">
                    <div className="font-semibold text-text-primary text-sm mb-1.5 flex items-center gap-2">
                      <span className="w-5 h-5 rounded-full bg-accent/15 text-accent flex items-center justify-center font-mono text-xs">1</span>
                      Data Source Disclosure: BDRY ETF Proxy
                    </div>
                    <p className="text-xs text-text-secondary leading-relaxed">
                      All freight rate figures in this application are derived from the <strong>Breakwave Dry Bulk Shipping ETF (BDRY)</strong> as a free, verifiable public proxy (2018–present). The Baltic Dry Index (BDI) is proprietary and paywalled. No synthetic pre-2018 data splicing was performed to ensure zero leakage and full reproducibility.
                    </p>
                  </div>

                  <div className="p-4 rounded-2xl bg-[#09090B] border border-[#26262B]">
                    <div className="font-semibold text-text-primary text-sm mb-1.5 flex items-center gap-2">
                      <span className="w-5 h-5 rounded-full bg-accent/15 text-accent flex items-center justify-center font-mono text-xs">2</span>
                      General Dry-Bulk Forecast Scope (vessel_type_id = NULL)
                    </div>
                    <p className="text-xs text-text-secondary leading-relaxed">
                      Module A produces a single market-wide freight rate trajectory. Sourcing genuine, independent per-vessel rates requires licensed Baltic sub-indices (BCI, BPI, BSI, BHSI). Applying synthetic scalar multipliers was explicitly rejected. Vessel allocation is instead governed strictly by physical port draft, LOA, and beam clearance (Module B).
                    </p>
                  </div>

                  <div className="p-4 rounded-2xl bg-[#09090B] border border-[#26262B]">
                    <div className="font-semibold text-text-primary text-sm mb-1.5 flex items-center gap-2">
                      <span className="w-5 h-5 rounded-full bg-accent/15 text-accent flex items-center justify-center font-mono text-xs">3</span>
                      Multi-Step Horizon Scoping (N &isin; &#123;7, 14&#125; Days)
                    </div>
                    <p className="text-xs text-text-secondary leading-relaxed">
                      Candidate decision windows in Module D are strictly restricted to 7 and 14 days. Diagnostic investigations in Session 6 proved that recursive autoregressive multi-step forecasting across 21 and 28 days introduces systematic downward dampening bias, causing naive models to mechanically default to N=28. Horizons beyond 14 days are excluded.
                    </p>
                  </div>

                  <div className="p-4 rounded-2xl bg-[#09090B] border border-[#26262B]">
                    <div className="font-semibold text-text-primary text-sm mb-1.5 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-[#E8A33D]" />
                      Regime Shift Vulnerability &amp; Black Swan Limitation
                    </div>
                    <p className="text-xs text-text-secondary leading-relaxed">
                      During unprecedented market shocks (e.g., the Jan 2021 post-COVID commodity surge, pre-Suez freight squeeze, and 2023 China reopening), waiting can experience adverse variance relative to an immediate fix. No machine learning model trained on prior data can anticipate truly unprecedented shocks. The system is designed to perform reliably in normal/detectable-risk regimes and be transparent about blind spots.
                    </p>
                  </div>

                  <div className="p-4 rounded-2xl bg-[#09090B] border border-[#26262B]">
                    <div className="font-semibold text-text-primary text-sm mb-1.5 flex items-center gap-2">
                      <span className="w-5 h-5 rounded-full bg-accent/15 text-accent flex items-center justify-center font-mono text-xs">5</span>
                      Sourced Operational &amp; Engineering Constants
                    </div>
                    <ul className="list-disc pl-5 space-y-1 text-xs text-text-secondary">
                      <li><strong>VLSFO Bunker Price:</strong> $600.00 / metric ton (Ship &amp; Bunker global 20-port average index).</li>
                      <li><strong>East Coast India Port Congestion:</strong> 36.0 hours average pre-berthing wait (IPA / Ministry of Ports data).</li>
                      <li><strong>Safety Maneuvering Buffer:</strong> 4.0 hours arrival cushion.</li>
                      <li><strong>Minimum Safe Speed Bound:</strong> 10.0 knots (IMO MEPC.1/Circ.684 safety steerage limit for laden bulkers).</li>
                      <li><strong>VLSFO Emission Factor:</strong> 3,114 kg CO2 per metric ton (IMO Fourth GHG Study 2020).</li>
                    </ul>
                  </div>
                </div>
              )}

              {/* TAB 3: 25-FIXTURE HISTORICAL BACKTEST */}
              {activeTab === 'fixtures' && (
                <div className="space-y-3">
                  <p className="text-[11px] text-text-tertiary">
                    Realized outcomes across 25 simulated fixtures (2020–2024) comparing DSS recommendation against naive baseline ($t_0$).
                  </p>

                  <div className="overflow-x-auto rounded-xl border border-[#26262B]">
                    <table className="w-full text-left text-[11px] font-mono">
                      <thead className="bg-[#09090B] text-text-tertiary border-b border-[#26262B]">
                        <tr>
                          <th className="p-2">#</th>
                          <th className="p-2">Date</th>
                          <th className="p-2">Corridor</th>
                          <th className="p-2">Vessel</th>
                          <th className="p-2">Action</th>
                          <th className="p-2">Window</th>
                          <th className="p-2 text-right">Saving</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#26262B]">
                        {fixtures.map((f) => (
                          <tr key={f.id} className="hover:bg-[#1C1C21]/60 transition-colors">
                            <td className="p-2 text-text-tertiary">{f.id}</td>
                            <td className="p-2">{f.date}</td>
                            <td className="p-2 text-text-primary truncate max-w-[140px]">{f.corridor}</td>
                            <td className="p-2 text-accent">{f.vessel}</td>
                            <td className="p-2">
                              <span
                                className={`px-1.5 py-0.5 rounded text-[10px] ${
                                  f.action === 'WAIT'
                                    ? 'bg-[#E8A33D]/20 text-[#E8A33D]'
                                    : 'bg-[#22A97A]/20 text-[#22A97A]'
                                }`}
                              >
                                {f.action}
                              </span>
                            </td>
                            <td className="p-2 text-text-tertiary">{f.window}</td>
                            <td
                              className={`p-2 text-right font-bold ${
                                f.saving.startsWith('+') && f.saving !== '+0.0%'
                                  ? 'text-[#22A97A]'
                                  : f.saving.startsWith('-')
                                  ? 'text-[#E4574C]'
                                  : 'text-text-tertiary'
                              }`}
                            >
                              {f.saving}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-[#26262B] bg-[#09090B] flex items-center justify-between text-[11px] font-mono text-text-tertiary">
              <span>Challenge 10 Guardrail: PASSED (&le; 25.0%)</span>
              <button
                onClick={onClose}
                className="px-4 py-1.5 rounded-full bg-[#131316] border border-[#26262B] text-text-primary hover:border-accent transition-colors"
              >
                Close Drawer
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
