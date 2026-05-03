import React from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer, Legend,
} from 'recharts';

/**
 * ForecastChart — Line chart with confidence-interval shaded band.
 * Highlights anomaly points with a red reference line.
 *
 * Props:
 *   history: Array<{ label: string, actual: number, forecast: number, q05: number, q95: number, anomaly: boolean }>
 */
export default function ForecastChart({ history }) {
  if (!history || history.length === 0) {
    return (
      <div className="card chart-placeholder">
        <p>Submit a reading to see the forecast chart.</p>
      </div>
    );
  }

  // Recharts Area uses [q05, q95] as a stacked band via "base" trick
  // We encode the band as: base = q05, band = q95 - q05
  const chartData = history.map(d => ({
    label: d.label,
    actual:       d.actual,
    forecast:     d.forecast,
    ci_lower:     d.q05,
    ci_band:      d.q95 != null && d.q05 != null ? +(d.q95 - d.q05).toFixed(4) : 0,
    anomaly:      d.anomaly,
  }));

  const anomalyLabels = chartData.filter(d => d.anomaly).map(d => d.label);

  return (
    <div className="card chart-card">
      <h2 className="card-title">Forecast vs. Actual</h2>
      <ResponsiveContainer width="100%" height={320}>
        <AreaChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#94a3b8' }} />
          <YAxis unit=" kWh" tick={{ fontSize: 11, fill: '#94a3b8' }} />
          <Tooltip
            contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
            labelStyle={{ color: '#94a3b8' }}
            itemStyle={{ color: '#e2e8f0' }}
            formatter={(v, name) => [v != null ? v.toFixed(3) + ' kWh' : '—', name]}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />

          {/* Confidence interval band */}
          <Area
            type="monotone"
            dataKey="ci_lower"
            stroke="none"
            fill="transparent"
            name="CI Lower"
            legendType="none"
          />
          <Area
            type="monotone"
            dataKey="ci_band"
            stackId="ci"
            stroke="none"
            fill="#3b82f6"
            fillOpacity={0.15}
            name="90% Confidence Band"
          />

          {/* Actual consumption */}
          <Area
            type="monotone"
            dataKey="actual"
            stroke="#38bdf8"
            strokeWidth={2}
            fill="none"
            dot={false}
            name="Actual (kWh)"
          />

          {/* Forecast */}
          <Area
            type="monotone"
            dataKey="forecast"
            stroke="#a78bfa"
            strokeWidth={2}
            strokeDasharray="5 4"
            fill="none"
            dot={false}
            name="Forecast (kWh)"
          />

          {/* Anomaly markers */}
          {anomalyLabels.map(label => (
            <ReferenceLine
              key={label}
              x={label}
              stroke="#ef4444"
              strokeDasharray="4 2"
              label={{ value: '⚠', position: 'top', fill: '#ef4444', fontSize: 12 }}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
