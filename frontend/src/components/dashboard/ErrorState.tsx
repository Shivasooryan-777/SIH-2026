import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
  error: string;
  onRetry: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({ error, onRetry }) => {
  return (
    <div className="w-full min-h-[380px] rounded-2xl bg-[#131316] border border-[#E4574C]/30 p-8 flex flex-col items-center justify-center text-center">
      <div className="w-14 h-14 rounded-full bg-[#E4574C]/10 border border-[#E4574C]/30 flex items-center justify-center text-[#E4574C] mb-4">
        <AlertCircle className="w-7 h-7" />
      </div>

      <h3 className="text-base font-semibold text-text-primary tracking-tight mb-2">
        Decision Evaluation Error
      </h3>

      <p className="text-xs text-text-secondary max-w-md mb-6 font-mono leading-relaxed bg-[#09090B] p-3 rounded-xl border border-[#26262B]">
        {error}
      </p>

      <button
        onClick={onRetry}
        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#1C1C21] border border-[#26262B] text-xs font-medium text-text-primary hover:border-accent hover:text-accent transition-colors"
      >
        <RefreshCw className="w-3.5 h-3.5" />
        <span>Retry Query</span>
      </button>
    </div>
  );
};
