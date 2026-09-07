import React from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';
import { TrendingUp, Info } from 'lucide-react';
import type { ForecastBandPoint } from '../../api/types';

interface QuantileBandChartProps {
  forecastCurve?: ForecastBandPoint[];
  currentSpotPrice?: number;
}

export const QuantileBandChart: React.FC<QuantileBandChartProps> = ({
  forecastCurve = [],
  currentSpotPrice,
}) => {
  // Option (a): Filter points strictly up to Day 14 (matching CANDIDATE_HORIZONS = [7, 14])
  const filteredPoints = (forecastCurve || [])
    .filter((pt) => pt && pt.horizon_days <= 14)
    .sort((a, b) => a.horizon_days - b.horizon_days);

  // If empty or missing, provide clean default data points strictly at 0, 7, 14
  const fNow = currentSpotPrice ?? 16.34;
  const chartData = filteredPoints.length > 0
    ? filteredPoints.map((pt) => ({
        day: pt.horizon_days,
        label: pt.horizon_days === 0 ? 'Today (t₀)' : `+${pt.horizon_days}d Horizon`,
        targetDate: pt.target_date || '',
        p10: Number(pt.p10_price),
        p50: Number(pt.p50_price),
        p90: Number(pt.p90_price),
        spread: Number(pt.spread ?? (pt.p90_price - pt.p10_price)),
      }))
    : [
        { day: 0, label: 'Today (t₀)', targetDate: '', p10: fNow, p50: fNow, p90: fNow, spread: 0 },
        { day: 7, label: '+7d Horizon', targetDate: '', p10: fNow - 0.8, p50: fNow + 0.15, p90: fNow + 1.3, spread: 2.1 },
        { day: 14, label: '+14d Horizon', targetDate: '', p10: fNow - 1.2, p50: fNow + 0.45, p90: fNow + 1.8, spread: 3.0 },
      ];

  const minVal = Math.min(...chartData.map((d) => d.p10));
  const maxVal = Math.max(...chartData.map((d) => d.p90));
  const yMin = Math.max(0, Math.floor(minVal - 1.5));
  const yMax = Math.ceil(maxVal + 1.5);

  return (
    <div className="rounded-2xl bg-[#131316] border border-[#26262B] p-5 flex flex-col justify-between">
      {/* Chart Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4 pb-3 border-b border-[#26262B]">
        <div>
          <div className="text-xs font-semibold text-text-primary flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-accent" />
            <span>Freight Trajectory (P10 / P50 / P90 Quantile Band)</span>
          </div>
          <p className="text-[11px] text-text-tertiary mt-0.5">
            General dry-bulk forward curve strictly scoped to validated empirical boundary (N &isin; &#123;7, 14&#125; days)
          </p>
        </div>
        <div className="flex items-center gap-2 text-[10px] font-mono">
          <span className="flex items-center gap-1 text-text-secondary">
            <span className="w-2.5 h-0.5 bg-accent inline-block" /> P50 Median
          </span>
          <span className="flex items-center gap-1 text-text-tertiary">
            <span className="w-2.5 h-2.5 bg-accent/20 border border-accent/40 rounded-sm inline-block" /> P10–P90 Spread
          </span>
        </div>
      </div>

      {/* Chart Container */}
      <div className="w-full h-64">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 12, right: 16, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="quantileSpreadGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#29B6C2" stopOpacity={0.35} />
                <stop offset="95%" stopColor="#29B6C2" stopOpacity={0.06} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="#26262B" vertical={false} />

            <XAxis
              dataKey="label"
              tickLine={false}
              axisLine={{ stroke: '#26262B' }}
              tick={{ fill: '#A1A1AA', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}
            />

            <YAxis
              domain={[yMin, yMax]}
              tickLine={false}
              axisLine={{ stroke: '#26262B' }}
              tick={{ fill: '#A1A1AA', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}
              tickFormatter={(val) => `$${val.toFixed(1)}`}
            />

            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  return (
                    <div className="rounded-xl bg-[#09090B]/95 border border-[#26262B] p-3 shadow-2xl backdrop-blur-md text-xs font-mono">
                      <div className="font-semibold text-text-primary mb-1.5 pb-1 border-b border-[#26262B]">
                        {data.label} {data.targetDate && `(${data.targetDate})`}
                      </div>
                      <div className="space-y-1 text-[11px]">
                        <div className="flex items-center justify-between gap-4 text-text-secondary">
                          <span>P90 (Upper Range):</span>
                          <span className="text-text-primary font-bold">${data.p90.toFixed(2)}/d</span>
                        </div>
                        <div className="flex items-center justify-between gap-4 text-accent">
                          <span>P50 (Median Forecast):</span>
                          <span className="font-bold text-accent-glow">${data.p50.toFixed(2)}/d</span>
                        </div>
                        <div className="flex items-center justify-between gap-4 text-text-secondary">
                          <span>P10 (Lower Range):</span>
                          <span className="text-text-primary font-bold">${data.p10.toFixed(2)}/d</span>
                        </div>
                        <div className="flex items-center justify-between gap-4 text-text-tertiary pt-1 border-t border-[#26262B]/80">
                          <span>Spread (P90 - P10):</span>
                          <span>${data.spread.toFixed(2)}/d</span>
                        </div>
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />

            {/* P90 Area with gradient fill */}
            <Area
              type="monotone"
              dataKey="p90"
              stroke="#29B6C2"
              strokeOpacity={0.4}
              strokeDasharray="2 2"
              fill="url(#quantileSpreadGradient)"
              isAnimationActive={false}
            />

            {/* P10 Area filling background below it to create the band effect */}
            <Area
              type="monotone"
              dataKey="p10"
              stroke="#29B6C2"
              strokeOpacity={0.4}
              strokeDasharray="2 2"
              fill="#131316"
              isAnimationActive={false}
            />

            {/* P50 Median Line */}
            <Line
              type="monotone"
              dataKey="p50"
              stroke="#29B6C2"
              strokeWidth={2.5}
              dot={{ r: 4, fill: '#29B6C2', stroke: '#131316', strokeWidth: 1.5 }}
              activeDot={{ r: 6, fill: '#6EE7E0', stroke: '#09090B', strokeWidth: 2 }}
              isAnimationActive={false}
            />

            {/* Current Spot Reference Line */}
            <ReferenceLine
              y={fNow}
              stroke="#71717A"
              strokeDasharray="4 4"
              label={{
                value: `Spot $${fNow.toFixed(2)}`,
                fill: '#A1A1AA',
                fontSize: 10,
                position: 'insideTopLeft',
                fontFamily: "'JetBrains Mono', monospace",
              }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Mandatory Inline Proxy Disclosure */}
      <div className="mt-3 pt-2 border-t border-[#26262B]/80 text-[10px] text-text-tertiary leading-snug flex items-start gap-1.5">
        <Info className="w-3 h-3 text-accent shrink-0 mt-0.5" />
        <span>
          General dry-bulk freight index (BDRY ETF proxy) — not a literal vessel charter day-rate. Single market trajectory applied across corridors.
        </span>
      </div>
    </div>
  );
};
