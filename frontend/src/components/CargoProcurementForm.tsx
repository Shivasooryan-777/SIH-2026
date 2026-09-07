import React, { useState, useEffect } from 'react';
import { Play, Sparkles, Navigation, AlertTriangle } from 'lucide-react';
import { Combobox } from './ui/Combobox';
import type { ComboboxOption } from './ui/Combobox';
import type { Port, Route, DecisionEvaluationRequest } from '../api/types';
import { fetchPorts, fetchRoutes } from '../api/client';

interface CargoProcurementFormProps {
  onSubmit: (payload: DecisionEvaluationRequest) => void;
  isLoading: boolean;
}

export const CargoProcurementForm: React.FC<CargoProcurementFormProps> = ({
  onSubmit,
  isLoading,
}) => {
  const [ports, setPorts] = useState<Port[]>([]);
  const [dataError, setDataError] = useState<string | null>(null);

  // Form states
  const [originPortId, setOriginPortId] = useState<number | null>(null);
  const [destPortId, setDestPortId] = useState<number | null>(null);
  const [cargoVolumeTons, setCargoVolumeTons] = useState<number>(75000);
  const [timeframeDays, setTimeframeDays] = useState<number>(30);
  const [contractPref, setContractPref] = useState<'spot' | 'period' | 'no_preference'>('spot');
  const [inTransit, setInTransit] = useState<boolean>(false);
  const [distanceRemainingNm, setDistanceRemainingNm] = useState<number>(1200);

  // Load ports and routes from backend
  useEffect(() => {
    let isMounted = true;
    async function loadReferenceData() {
      try {
        const [portsData, routesData] = await Promise.all([fetchPorts(), fetchRoutes()]);
        if (isMounted) {
          if (Array.isArray(portsData)) {
            setPorts(portsData);
          }
          // Set default pair from first available route if available
          if (Array.isArray(routesData) && routesData.length > 0) {
            setOriginPortId(routesData[0].origin_port_id);
            setDestPortId(routesData[0].destination_port_id);
          }
        }
      } catch (err: any) {
        if (isMounted) {
          setDataError(err.message || 'Failed to load master ports from Neon database');
        }
      }
    }
    loadReferenceData();
    return () => {
      isMounted = false;
    };
  }, []);

  // Build options for Combobox with array safety
  const originOptions: ComboboxOption[] = (Array.isArray(ports) ? ports : [])
    .filter((p) => p && p.port_role === 'origin')
    .map((p) => ({
      value: p.port_id,
      label: p.name,
      sublabel: `${p.country} • Max Draft ${p.baseline_draft_m}m`,
      group: 'Overseas Origins',
    }));

  const destOptions: ComboboxOption[] = (Array.isArray(ports) ? ports : [])
    .filter((p) => p && p.port_role === 'destination')
    .map((p) => ({
      value: p.port_id,
      label: p.name,
      sublabel: `India • Max Draft ${p.baseline_draft_m}m`,
      group: 'East Coast India',
    }));

  const contractOptions: ComboboxOption[] = [
    { value: 'spot', label: 'Spot Voyage Charter', sublabel: 'Single fixture procurement', group: 'Contracting Policy' },
    { value: 'period', label: 'Period Time Charter', sublabel: 'Short/medium term fixture', group: 'Contracting Policy' },
    { value: 'no_preference', label: 'No Preference', sublabel: 'Model selects optimal regime', group: 'Contracting Policy' },
  ];

  // Quick preset helper
  const applyPreset = (origName: string, destName: string, volume: number) => {
    const o = ports.find((p) => p.name.toLowerCase().includes(origName.toLowerCase()));
    const d = ports.find((p) => p.name.toLowerCase().includes(destName.toLowerCase()));
    if (o) setOriginPortId(o.port_id);
    if (d) setDestPortId(d.port_id);
    setCargoVolumeTons(volume);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!originPortId || !destPortId) return;

    onSubmit({
      cargo_type: 'coking_coal',
      cargo_volume_tons: cargoVolumeTons,
      origin_port_id: originPortId,
      destination_port_id: destPortId,
      desired_timeframe_days: timeframeDays,
      desired_contract_pref: contractPref,
      vessel_in_transit: inTransit,
      distance_remaining_nm: inTransit ? distanceRemainingNm : undefined,
    });
  };

  return (
    <div className="w-full bg-[#131316] rounded-2xl border border-[#26262B] p-5">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-[#26262B]">
        <div>
          <h2 className="text-sm font-semibold text-text-primary tracking-tight">
            Cargo Procurement Query
          </h2>
          <p className="text-xs text-text-tertiary">Configure voyage &amp; vessel parameters</p>
        </div>
        <div className="flex items-center gap-1 text-[11px] font-mono text-accent">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Modules A–E</span>
        </div>
      </div>

      {dataError && (
        <div className="mb-4 p-3 rounded-xl bg-[#E4574C]/10 border border-[#E4574C]/30 text-xs text-[#E4574C] flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{dataError}</span>
        </div>
      )}

      {/* Quick Corridors Presets */}
      <div className="mb-5">
        <label className="block text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-2">
          Fast Presets (Historical Corridors)
        </label>
        <div className="flex flex-wrap gap-1.5">
          <button
            type="button"
            onClick={() => applyPreset('Taboneo', 'Haldia', 55000)}
            className="px-2.5 py-1 rounded-full text-[11px] font-mono bg-[#09090B] border border-[#26262B] text-text-secondary hover:text-text-primary hover:border-accent transition-colors"
          >
            Taboneo → Haldia (55,000 MT)
          </button>
          <button
            type="button"
            onClick={() => applyPreset('Newcastle', 'Paradip', 150000)}
            className="px-2.5 py-1 rounded-full text-[11px] font-mono bg-[#09090B] border border-[#26262B] text-text-secondary hover:text-text-primary hover:border-accent transition-colors"
          >
            Newcastle → Paradip (150,000 MT)
          </button>
          <button
            type="button"
            onClick={() => applyPreset('Maputo', 'Dhamra', 75000)}
            className="px-2.5 py-1 rounded-full text-[11px] font-mono bg-[#09090B] border border-[#26262B] text-text-secondary hover:text-text-primary hover:border-accent transition-colors"
          >
            Maputo → Dhamra (75,000 MT)
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Origin Port Searchable Combobox */}
        <Combobox
          label="Origin (Loading Port)"
          placeholder="Select loading port..."
          options={originOptions}
          value={originPortId}
          onChange={(val) => setOriginPortId(Number(val))}
          required
        />

        {/* Destination Port Searchable Combobox */}
        <Combobox
          label="Destination (East Coast Discharge)"
          placeholder="Select discharge port..."
          options={destOptions}
          value={destPortId}
          onChange={(val) => setDestPortId(Number(val))}
          required
        />

        {/* Cargo Volume (tons) */}
        <div>
          <label className="block text-xs font-medium text-text-secondary mb-1.5 flex items-center justify-between">
            <span>Cargo Volume (Metric Tons) <span className="text-accent">*</span></span>
            <span className="text-[11px] font-mono text-text-tertiary">
              {cargoVolumeTons.toLocaleString()} MT
            </span>
          </label>
          <div className="relative">
            <input
              type="number"
              min="10000"
              max="250000"
              step="5000"
              value={cargoVolumeTons}
              onChange={(e) => setCargoVolumeTons(Number(e.target.value))}
              className="w-full h-11 px-3.5 rounded-2xl bg-[#131316] border border-[#26262B] font-mono text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all"
            />
          </div>
        </div>

        {/* Laycan Window (days) */}
        <div>
          <label className="block text-xs font-medium text-text-secondary mb-1.5 flex items-center justify-between">
            <span>Laycan Window (Days Forward) <span className="text-accent">*</span></span>
            <span className="text-[11px] font-mono text-text-tertiary">
              {timeframeDays} days
            </span>
          </label>
          <div className="relative">
            <input
              type="number"
              min="7"
              max="60"
              value={timeframeDays}
              onChange={(e) => setTimeframeDays(Number(e.target.value))}
              className="w-full h-11 px-3.5 rounded-2xl bg-[#131316] border border-[#26262B] font-mono text-sm text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all"
            />
            <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-mono text-text-tertiary">
              days
            </span>
          </div>
        </div>

        {/* Contract Preference Combobox - Full width to prevent any text clipping */}
        <div>
          <Combobox
            label="Contract Structuring Preference"
            options={contractOptions}
            value={contractPref}
            onChange={(val) => setContractPref(val as any)}
          />
        </div>

        {/* In-Transit Toggle (Triggers Module E2) */}
        <div className="pt-2 border-t border-[#26262B]">
          <label className="flex items-start gap-3 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={inTransit}
              onChange={(e) => setInTransit(e.target.checked)}
              className="mt-1 w-4 h-4 rounded-md border-[#26262B] bg-[#09090B] text-accent focus:ring-accent focus:ring-offset-0 focus:ring-1 cursor-pointer accent-[#29B6C2]"
            />
            <div className="flex flex-col">
              <span className="text-xs font-medium text-text-primary flex items-center gap-1.5">
                <Navigation className="w-3.5 h-3.5 text-accent" />
                Vessel Currently in Transit
              </span>
              <span className="text-[11px] text-text-tertiary mt-0.5">
                Evaluates Module E2 JIT speed reduction into East Coast berth queue
              </span>
            </div>
          </label>

          {inTransit && (
            <div className="mt-3 pl-7">
              <label className="block text-xs font-medium text-text-secondary mb-1">
                Distance Remaining to Discharge Port
              </label>
              <div className="relative">
                <input
                  type="number"
                  min="100"
                  max="12000"
                  step="50"
                  value={distanceRemainingNm}
                  onChange={(e) => setDistanceRemainingNm(Number(e.target.value))}
                  className="w-full h-10 px-3 rounded-2xl bg-[#09090B] border border-[#26262B] font-mono text-xs text-text-primary focus:outline-none focus:border-accent"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-mono text-text-tertiary">
                  nm
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Primary CTA Evaluate Button */}
        <button
          type="submit"
          disabled={isLoading || !originPortId || !destPortId}
          className="w-full h-12 rounded-full bg-accent text-[#09090B] font-semibold text-sm flex items-center justify-center gap-2 transition-all duration-200 hover:bg-[#6EE7E0] hover:shadow-[0_0_25px_rgba(41,182,194,0.35)] active:scale-[0.99] disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
        >
          {isLoading ? (
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 border-2 border-[#09090B] border-t-transparent rounded-full animate-spin" />
              <span>Evaluating Multi-Module Engines...</span>
            </div>
          ) : (
            <>
              <Play className="w-4 h-4 fill-current" />
              <span>Evaluate Chartering Decision</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
};
