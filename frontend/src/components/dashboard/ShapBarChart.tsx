import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';
import { Layers, ArrowUpRight, ArrowDownRight, Info } from 'lucide-react';
import type { ShapItem } from '../../api/types';

interface ShapBarChartProps {
  shapExplanations?: ShapItem[];
}

export const ShapBarChart: React.FC<ShapBarChartProps> = ({
  shapExplanations = [],
}) => {
  // Use actual live database feature_name strings
  const rawItems = (shapExplanations || []).length > 0
    ? shapExplanations
    : [
        { feature_name: 'freight_lag_7', contribution_pct: 38.5, direction: 'upward' as const },
        { feature_name: 'brent_crude', contribution_pct: 32.2, direction: 'upward' as const },
        { feature_name: 'iron_ore_62', contribution_pct: 29.3, direction: 'downward' as const },
      ];

  // Format data for horizontal diverging chart
  // Positive value for upward, negative value for downward
  const chartData = rawItems.map((item) => {
    const isUpward = item.direction === 'upward';
    const signedValue = isUpward
      ? Math.abs(item.contribution_pct)
      : -Math.abs(item.contribution_pct);

    return {
      feature: item.feature_name,
      displayName: item.feature_name.replace(/_/g, ' '),
      pct: item.contribution_pct,
      value: signedValue,
      direction: item.direction,
      color: isUpward ? '#29B6C2' : '#E4574C',
    };
  });

  return (
    <div className="rounded-2xl bg-[#131316] border border-[#26262B] p-5 flex flex-col justify-between">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4 pb-3 border-b border-[#26262B]">
        <div>
          <div className="text-xs font-semibold text-text-primary flex items-center gap-2">
            <Layers className="w-4 h-4 text-accent" />
            <span>Market Drivers (SHAP TreeExplainer Attributions)</span>
          </div>
          <p className="text-[11px] text-text-tertiary mt-0.5">
            Top feature impact on median P50 freight prediction (direct database columns)
          </p>
        </div>
        <div className="flex items-center gap-3 text-[10px] font-mono">
          <span className="flex items-center gap-1 text-[#29B6C2]">
            <ArrowUpRight className="w-3 h-3" /> Upward Push
          </span>
          <span className="flex items-center gap-1 text-[#E4574C]">
            <ArrowDownRight className="w-3 h-3" /> Downward Drag
          </span>
        </div>
      </div>

      {/* Chart */}
      <div className="w-full h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 8, right: 30, left: 24, bottom: 8 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#26262B" horizontal={false} />

            <XAxis
              type="number"
              domain={[-60, 60]}
              tickLine={false}
              axisLine={{ stroke: '#26262B' }}
              tick={{ fill: '#A1A1AA', fontSize: 10, fontFamily: "'JetBrains Mono', monospace" }}
              tickFormatter={(v) => `${Math.abs(v)}%`}
            />

            <YAxis
              type="category"
              dataKey="feature"
              tickLine={false}
              axisLine={{ stroke: '#26262B' }}
              tick={{ fill: '#F4F4F5', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}
              width={110}
            />

            <Tooltip
              cursor={{ fill: 'rgba(255, 255, 255, 0.03)' }}
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  const isUp = data.direction === 'upward';
                  return (
                    <div className="rounded-xl bg-[#09090B]/95 border border-[#26262B] p-3 shadow-2xl backdrop-blur-md text-xs font-mono">
                      <div className="font-semibold text-text-primary mb-1 pb-1 border-b border-[#26262B]">
                        Feature: {data.feature}
                      </div>
                      <div className="text-[11px] space-y-1 mt-1">
                        <div className="flex items-center justify-between gap-4">
                          <span className="text-text-secondary">Attribution Impact:</span>
                          <span className="font-bold text-text-primary">{data.pct.toFixed(2)}%</span>
                        </div>
                        <div className="flex items-center justify-between gap-4">
                          <span className="text-text-secondary">Direction:</span>
                          <span
                            className="font-bold uppercase"
                            style={{ color: isUp ? '#29B6C2' : '#E4574C' }}
                          >
                            {isUp ? '↑ Upward Pressure' : '↓ Downward Drag'}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />

            <ReferenceLine x={0} stroke="#3F3F46" strokeWidth={1.5} />

            <Bar dataKey="value" radius={[4, 4, 4, 4]} barSize={16}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Feature Footnote */}
      <div className="mt-3 pt-2 border-t border-[#26262B]/80 text-[10px] text-text-tertiary leading-snug flex items-start gap-1.5">
        <Info className="w-3 h-3 text-accent shrink-0 mt-0.5" />
        <span>
          Attributions computed via TreeExplainer on fitted P50 LightGBM/XGBoost models using trailing macro &amp; freight momentum indicators.
        </span>
      </div>
    </div>
  );
};
