import { Compass, Sparkles, Shield, Cpu } from 'lucide-react';

export const EmptyState: React.FC = () => {
  return (
    <div className="w-full h-full min-h-[440px] rounded-2xl bg-[#131316] border border-[#26262B] p-8 flex flex-col items-center justify-center text-center">
      {/* Visual Compass Device */}
      <div className="relative mb-6">
        <div className="w-20 h-20 rounded-full bg-[#09090B] border border-[#26262B] flex items-center justify-center text-accent">
          <Compass className="w-10 h-10 animate-pulse" />
        </div>
        <div className="absolute -inset-2 rounded-full border border-accent/20 border-dashed animate-[spin_40s_linear_infinite]" />
      </div>

      <h3 className="text-lg font-semibold text-text-primary tracking-tight mb-2">
        Decision Cockpit Standby
      </h3>

      <p className="text-sm text-text-secondary max-w-md mb-8 leading-relaxed">
        Select your overseas origin port, East Coast India discharge port, and volume
        to compute the multi-module chartering evaluation.
      </p>

      {/* Feature Pills */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full max-w-lg text-left">
        <div className="p-3.5 rounded-2xl bg-[#09090B] border border-[#26262B]">
          <div className="flex items-center gap-2 text-xs font-semibold text-text-primary mb-1">
            <Cpu className="w-3.5 h-3.5 text-accent" />
            <span>Walk-Forward ML</span>
          </div>
          <p className="text-[11px] text-text-tertiary">
            P10/P50/P90 quantile band price projection without lookahead leakage.
          </p>
        </div>

        <div className="p-3.5 rounded-2xl bg-[#09090B] border border-[#26262B]">
          <div className="flex items-center gap-2 text-xs font-semibold text-text-primary mb-1">
            <Sparkles className="w-3.5 h-3.5 text-[#22A97A]" />
            <span>Dynamic Draft</span>
          </div>
          <p className="text-[11px] text-text-tertiary">
            Physical LOA, beam, and seasonal draft constraints check per port.
          </p>
        </div>

        <div className="p-3.5 rounded-2xl bg-[#09090B] border border-[#26262B]">
          <div className="flex items-center gap-2 text-xs font-semibold text-text-primary mb-1">
            <Shield className="w-3.5 h-3.5 text-[#E8A33D]" />
            <span>Expected Value</span>
          </div>
          <p className="text-[11px] text-text-tertiary">
            Quantified FIX NOW vs WAIT recommendation with risk adjustment.
          </p>
        </div>
      </div>
    </div>
  );
};
