import React, { useState, useEffect } from 'react';

export const LoadingSkeleton: React.FC = () => {
  const steps = [
    'Verifying dynamic port draft advisories and LOA bounds (Module B)...',
    'Executing walk-forward quantile forecast P10/P50/P90 (Module A)...',
    'Computing SHAP feature attribution vectors (Module A)...',
    'Checking route risk flags and macro volatility (Module C)...',
    'Evaluating expected value arbitrage FIX vs WAIT (Module D)...',
    'Optimizing spot-vs-period trough & JIT arrival (Module E)...',
  ];

  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev < steps.length - 1 ? prev + 1 : prev));
    }, 600);
    return () => clearInterval(interval);
  }, [steps.length]);

  return (
    <div className="w-full space-y-4 animate-pulse">
      {/* Step Indicator Header */}
      <div className="p-4 rounded-2xl bg-[#131316] border border-accent/40 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          <span className="text-xs font-medium text-text-primary">
            {steps[activeStep]}
          </span>
        </div>
        <span className="text-xs font-mono text-accent">
          Step {activeStep + 1}/{steps.length}
        </span>
      </div>

      {/* Hero Card Skeleton */}
      <div className="h-44 rounded-2xl bg-[#131316] border border-[#26262B] p-6 flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <div className="w-32 h-6 rounded-full bg-[#1C1C21]" />
          <div className="w-24 h-5 rounded-full bg-[#1C1C21]" />
        </div>
        <div className="space-y-2">
          <div className="w-48 h-8 rounded-xl bg-[#1C1C21]" />
          <div className="w-64 h-4 rounded-lg bg-[#1C1C21]" />
        </div>
        <div className="w-full h-3 rounded-lg bg-[#1C1C21]" />
      </div>

      {/* Two Column Skeletons */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="h-52 rounded-2xl bg-[#131316] border border-[#26262B] p-5 space-y-3">
          <div className="w-28 h-5 rounded-full bg-[#1C1C21]" />
          <div className="w-full h-8 rounded-xl bg-[#1C1C21]" />
          <div className="w-full h-8 rounded-xl bg-[#1C1C21]" />
          <div className="w-3/4 h-8 rounded-xl bg-[#1C1C21]" />
        </div>
        <div className="h-52 rounded-2xl bg-[#131316] border border-[#26262B] p-5 space-y-3">
          <div className="w-28 h-5 rounded-full bg-[#1C1C21]" />
          <div className="w-full h-24 rounded-xl bg-[#1C1C21]" />
          <div className="w-1/2 h-6 rounded-lg bg-[#1C1C21]" />
        </div>
      </div>

      {/* Chart Skeleton */}
      <div className="h-64 rounded-2xl bg-[#131316] border border-[#26262B] p-6 space-y-4">
        <div className="flex justify-between items-center">
          <div className="w-40 h-5 rounded-full bg-[#1C1C21]" />
          <div className="w-20 h-4 rounded-full bg-[#1C1C21]" />
        </div>
        <div className="w-full h-44 rounded-xl bg-[#1C1C21]" />
      </div>
    </div>
  );
};
