import React, { useState, useEffect } from 'react';
import { Check, Send, CheckCircle2, MessageSquare, X } from 'lucide-react';
import { markDecisionActioned } from '../../api/client';

interface ActionConfirmButtonProps {
  decisionId: number;
}

export const ActionConfirmButton: React.FC<ActionConfirmButtonProps> = ({
  decisionId,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [note, setNote] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionedData, setActionedData] = useState<{
    actionId: number;
    actionedAt: string;
  } | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false);
    };
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const handleConfirmAction = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setActionError(null);

    try {
      const res = await markDecisionActioned(
        decisionId,
        note.trim() || undefined
      );
      setActionedData({
        actionId: res.action_id,
        actionedAt: res.actioned_at,
      });
      setIsOpen(false);
    } catch (err: any) {
      setActionError(err.message || 'Failed to log actioned decision');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (actionedData) {
    const formattedDate = new Date(actionedData.actionedAt).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'UTC',
    });

    return (
      <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#22A97A]/15 border border-[#22A97A]/40 text-xs font-mono text-[#22A97A]">
        <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
        <span>Actioned #{actionedData.actionId} ({formattedDate} UTC)</span>
      </div>
    );
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#09090B] border border-[#26262B] text-xs font-mono text-text-primary hover:border-accent hover:text-accent transition-all duration-200 shadow-sm"
      >
        <Check className="w-3.5 h-3.5 text-accent" />
        <span>Mark as Actioned</span>
      </button>

      {/* Centered Modal Dialog with Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#09090B]/80 backdrop-blur-sm"
          onClick={() => setIsOpen(false)}
        >
          <div
            className="w-full max-w-md p-5 rounded-2xl bg-[#131316] border border-[#26262B] shadow-2xl relative"
            onClick={(e) => e.stopPropagation()}
          >
            <form onSubmit={handleConfirmAction} className="space-y-3.5">
              <div className="flex items-center justify-between pb-2 border-b border-[#26262B]">
                <span className="font-semibold text-text-primary text-sm flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-accent" />
                  Log Fixture Execution (Module F)
                </span>
                <button
                  type="button"
                  onClick={() => setIsOpen(false)}
                  className="w-7 h-7 rounded-lg bg-[#09090B] border border-[#26262B] flex items-center justify-center text-text-tertiary hover:text-text-primary text-xs transition-colors"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>

              <p className="text-xs text-text-secondary leading-relaxed">
                Confirm that this chartering recommendation was executed by the operations desk. This creates a timestamped audit record in the Neon Postgres database.
              </p>

              <div>
                <label className="block text-[10px] uppercase font-mono text-text-tertiary mb-1">
                  Operational Execution Note (Optional)
                </label>
                <input
                  type="text"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="e.g. Fixture confirmed with Newcastle chartering desk"
                  className="w-full h-9 px-3 rounded-xl bg-[#09090B] border border-[#26262B] text-xs font-mono text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent"
                  autoFocus
                />
              </div>

              {actionError && (
                <div className="text-xs text-[#E4574C] font-mono">{actionError}</div>
              )}

              <div className="flex items-center justify-end gap-2.5 pt-2">
                <button
                  type="button"
                  onClick={() => setIsOpen(false)}
                  className="px-3.5 py-1.5 rounded-full text-text-tertiary hover:text-text-primary font-mono text-xs border border-transparent hover:border-[#26262B] transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full bg-accent text-[#09090B] font-semibold font-mono text-xs hover:bg-accent-glow transition-colors disabled:opacity-50 shadow-sm"
                >
                  <Send className="w-3 h-3" />
                  <span>{isSubmitting ? 'Logging...' : 'Confirm Action'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
};
