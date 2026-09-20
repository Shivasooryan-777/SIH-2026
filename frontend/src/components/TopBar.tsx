import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Ship, Activity, Sliders, ArrowLeft } from 'lucide-react';
import { fetchHealth, fetchMarketWatch } from '../api/client';
import type { MarketWatchResponse, ActiveRiskFlag } from '../api/types';
import { ThemeToggle } from './ThemeToggle';

interface TopBarProps {
  onOpenTransparency?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({ onOpenTransparency }) => {
  const navigate = useNavigate();

  // Health state
  const [dbHealthy, setDbHealthy] = useState<boolean | null>(null);

  // Market Watch state
  const [marketWatch, setMarketWatch] = useState<MarketWatchResponse | null>(null);

  // Poll health and market watch
  useEffect(() => {
    let isMounted = true;

    async function loadHealth() {
      try {
        const res = await fetchHealth();
        if (isMounted) setDbHealthy(res.status === 'healthy' && res.database === 'connected');
      } catch {
        if (isMounted) setDbHealthy(false);
      }
    }

    async function loadMarketWatch() {
      try {
        const data = await fetchMarketWatch();
        if (isMounted) {
          setMarketWatch(data);
        }
      } catch {
        if (isMounted) {
          setMarketWatch(null);
        }
      }
    }

    loadHealth();
    loadMarketWatch();

    // 30s polling intervals
    const healthInterval = setInterval(loadHealth, 30000);
    const mwInterval = setInterval(loadMarketWatch, 25000);

    return () => {
      isMounted = false;
      clearInterval(healthInterval);
      clearInterval(mwInterval);
    };
  }, []);

  // Helper to color dots per locked palette
  const getRiskDotColor = (level?: string | null) => {
    switch ((level || 'calm').toLowerCase()) {
      case 'high':
        return 'var(--color-danger)';
      case 'elevated':
        return 'var(--color-warning)';
      case 'calm':
      default:
        return 'var(--color-positive)';
    }
  };

  const getRiskBadgeClass = (level?: string | null) => {
    switch ((level || 'calm').toLowerCase()) {
      case 'high':
        return 'bg-semantic-risk/20 text-semantic-risk';
      case 'elevated':
        return 'bg-semantic-wait/20 text-semantic-wait';
      case 'calm':
      default:
        return 'bg-semantic-positive/20 text-semantic-positive';
    }
  };

  // 8 standard corridors to display in ticker (enriched with active flags if present)
  const defaultCorridors = [
    { name: 'Taboneo → Haldia', risk: 'calm', reason: 'Normal voyage speed' },
    { name: 'Taboneo → Paradip', risk: 'calm', reason: 'Open draft conditions' },
    { name: 'Maputo → Dhamra', risk: 'calm', reason: 'Monsoon draft monitoring' },
    { name: 'Beira → Dhamra', risk: 'calm', reason: 'Stable cape route' },
    { name: 'Nacala → Gangavaram', risk: 'calm', reason: 'Capesize deep water berth' },
    { name: 'Vostochny → Vizag', risk: 'calm', reason: 'Outer harbour unrestricted' },
    { name: 'Newcastle → Paradip', risk: 'calm', reason: 'SPM deep draft' },
    { name: 'Lamberts Point → Vizag', risk: 'calm', reason: 'Standard transit' },
  ];

  const activeFlags = Array.isArray(marketWatch?.active_flags) ? marketWatch.active_flags : [];

  // Extract any global macro disruption flags (route_id is null)
  const macroItems = activeFlags
    .filter((f: ActiveRiskFlag) => !f.route_id || (f.corridor && f.corridor.toLowerCase().includes('global macro')))
    .map((f: ActiveRiskFlag) => {
      let label = 'Global Macro Disruption';
      if (f.reason) {
        const clean = f.reason
          .replace(/^HIGH RISK\s*—\s*Active disruption alert:\s*/i, '')
          .replace(/^ELEVATED RISK\s*—\s*/i, '')
          .replace(/^CALM\s*—\s*/i, '')
          .split('(Event:')[0]
          .split('.')[0]
          .trim();
        if (clean) label = `Macro Alert: ${clean}`;
      }
      return {
        name: label,
        risk: f.risk_level || 'high',
        reason: f.reason || 'Active global macro disruption event',
      };
    });

  // Map active flags over standard corridors
  const corridorItems = defaultCorridors.map((corridor) => {
    const activeFlag = activeFlags.find((f: ActiveRiskFlag) => {
      if (!f || !f.corridor || !f.route_id) return false;
      const parts = f.corridor.split('->');
      const orig = (parts[0] || '').trim().toLowerCase();
      const dest = (parts[1] || '').trim().toLowerCase();
      return (
        corridor.name.toLowerCase().includes(orig) ||
        (dest && corridor.name.toLowerCase().includes(dest))
      );
    });
    if (activeFlag) {
      return {
        name: corridor.name,
        risk: activeFlag.risk_level || 'calm',
        reason: activeFlag.reason || 'Active corridor watch',
      };
    }
    return corridor;
  });

  // Combine: Macro alerts first (explaining any elevated/high overall sentiment), followed by 8 corridors
  const tickerItems = [...macroItems, ...corridorItems];

  return (
    <header className="w-full bg-canvas border-b border-border sticky top-0 z-40">
      {/* Upper Navigation Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        {/* Left: Branding & Back Button */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/')}
            title="Return to Landing Page"
            className="w-9 h-9 rounded-2xl bg-surface border border-border flex items-center justify-center text-text-secondary hover:text-text-primary hover:border-text-secondary/50 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>

          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-surface border border-border flex items-center justify-center text-accent">
              <Ship className="w-4 h-4" />
            </div>
            <div>
              <div className="text-sm font-semibold tracking-tight text-text-primary flex items-center gap-2">
                <span>NAV-STEEL DSS</span>
                <span className="hidden sm:inline text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-surface border border-border text-accent">
                  SIH26006
                </span>
              </div>
              <div className="text-[11px] text-text-tertiary">
                East Coast India Bulk Procurement
              </div>
            </div>
          </div>
        </div>

        {/* Center / Right: DB Health Pill & Transparency Trigger */}
        <div className="flex items-center gap-3">
          {/* Neon DB Health Pill */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface border border-border text-xs font-mono">
            <span
              className={`w-2 h-2 rounded-full shrink-0 ${
                dbHealthy === true
                  ? 'bg-semantic-positive'
                  : dbHealthy === false
                  ? 'bg-semantic-risk'
                  : 'bg-semantic-wait'
              }`}
            />
            <span className="hidden md:inline text-text-secondary">NEON DB</span>
            <span
              className={`font-medium ${
                dbHealthy === true
                  ? 'text-semantic-positive'
                  : dbHealthy === false
                  ? 'text-semantic-risk'
                  : 'text-semantic-wait'
              }`}
            >
              {dbHealthy === true ? 'CONNECTED' : dbHealthy === false ? 'DISCONNECTED' : 'CHECKING...'}
            </span>
          </div>

          {/* Theme Toggle */}
          <ThemeToggle />

          {/* Model Transparency Drawer Trigger */}
          {onOpenTransparency && (
            <button
              onClick={onOpenTransparency}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-surface border border-border text-xs font-medium text-text-secondary hover:text-text-primary hover:border-accent transition-colors"
            >
              <Sliders className="w-3.5 h-3.5 text-accent" />
              <span className="hidden sm:inline">Transparency &amp; Disclosures</span>
            </button>
          )}
        </div>
      </div>

      {/* Always-On Market Watch Ticker Strip */}
      <div className="w-full bg-surface border-t border-border py-2 px-4 overflow-hidden relative">
        {/* Desktop / Tablet: Auto-scrolling Strip (pauses on hover) */}
        <div className="hidden md:flex items-center">
          {/* Sentiment Anchor Tag */}
          <div className="shrink-0 pr-4 mr-2 border-r border-border flex items-center gap-2 text-xs">
            <Activity className="w-3.5 h-3.5 text-accent" />
            <span className="text-[11px] font-semibold tracking-wider text-text-secondary uppercase">
              MARKET WATCH:
            </span>
            <span
              className={`px-2 py-0.5 rounded-full text-[10px] font-mono uppercase font-bold ${getRiskBadgeClass(marketWatch?.overall_sentiment)}`}
            >
              {marketWatch?.overall_sentiment || 'CALM'}
            </span>
          </div>

          {/* Continuous Ticker */}
          <div className="overflow-hidden flex-1 relative">
            <div className="animate-ticker flex items-center gap-8 cursor-default">
              {tickerItems.concat(tickerItems).map((item, idx) => (
                <div
                  key={idx}
                  title={item.reason}
                  className="flex items-center gap-2 shrink-0 text-xs hover:opacity-80 transition-opacity cursor-pointer"
                >
                  <span
                    className="w-1.5 h-1.5 rounded-full shrink-0"
                    style={{ backgroundColor: getRiskDotColor(item.risk) }}
                  />
                  <span className="text-text-primary font-medium">{item.name}</span>
                  <span
                    className="text-[11px] font-mono font-semibold"
                    style={{ color: getRiskDotColor(item.risk) }}
                  >
                    [{item.risk.toUpperCase()}]
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Mobile: Compact Non-scrolling Summary Bar */}
        <div className="flex md:hidden items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <Activity className="w-3.5 h-3.5 text-accent" />
            <span className="text-text-secondary text-[11px] font-medium">Market:</span>
            <span
              className={`px-2 py-0.5 rounded-full text-[10px] font-mono uppercase font-bold ${getRiskBadgeClass(marketWatch?.overall_sentiment)}`}
            >
              {marketWatch?.overall_sentiment || 'CALM'}
            </span>
          </div>
          <div className="text-[11px] font-mono text-text-tertiary">
            {marketWatch?.active_flags_count || 0} active flags
          </div>
        </div>
      </div>
    </header>
  );
};
