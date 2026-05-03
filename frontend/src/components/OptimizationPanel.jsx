import React from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts';

/**
 * OptimizationPanel — Visualizes before vs after load profile and extrapolated cost impact.
 */
export default function OptimizationPanel({ optimization }) {
  if (!optimization) {
    return (
      <div className="card opt-placeholder">
        <p>Enable "Run Optimizer" to calculate 48-hour shifting constraints.</p>
      </div>
    );
  }

  const { original_cost, optimized_cost, savings, original_profile, optimized_profile } = optimization;

  // Build chart array from 48-length lists
  const chartData = [];
  if (original_profile && optimized_profile && original_profile.length === 48) {
    for (let i = 0; i < 48; i++) {
      chartData.push({
        hour: i,
        OriginalLoad: original_profile[i],
        OptimizedLoad: optimized_profile[i]
      });
    }
  }

  return (
    <div className="card opt-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h2 className="card-title" style={{ margin: 0 }}>LP Cost Optimization</h2>
        <span style={{ fontSize: '0.75rem', fontWeight: 600, padding: '4px 8px', borderRadius: '4px', background: '#334155', color: '#cbd5e1' }}>
          Horizon: 48 Hours
        </span>
      </div>

      <div className="opt-summary" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <div className="opt-stat">
          <span className="opt-label">Base Cost</span>
          <strong className="opt-value orange">Rs. {original_cost?.toFixed(2)}</strong>
        </div>
        <div className="opt-stat">
          <span className="opt-label">Optimized</span>
          <strong className="opt-value green">Rs. {optimized_cost?.toFixed(2)}</strong>
        </div>
        <div className="opt-stat">
          <span className="opt-label">48h Savings</span>
          <strong className="opt-value blue">Rs. {savings?.toFixed(2)}</strong>
        </div>
        <div className="opt-stat" style={{ borderLeft: '1px solid #334155', paddingLeft: '12px' }}>
          <span className="opt-label">Monthly Impact</span>
          <strong className="opt-value" style={{ color: '#e2e8f0' }}>
            ~Rs. {((savings / 2) * 30).toFixed(0)}
          </strong>
        </div>
      </div>

      {chartData.length > 0 && (
        <div style={{ marginTop: '24px' }}>
          <h3 style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '12px' }}>Before vs After Load Profile (48h)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorOrig" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.6}/>
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorOpt" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22c55e" stopOpacity={0.6}/>
                  <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="hour" tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis unit=" kWh" tick={{ fill: '#64748b', fontSize: 11 }} />
              <Tooltip 
                contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8, fontSize: '0.8rem' }}
              />
              <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '0.85rem' }}/>
              <Area type="monotone" dataKey="OriginalLoad" stroke="#f59e0b" fillOpacity={1} fill="url(#colorOrig)" />
              <Area type="monotone" dataKey="OptimizedLoad" stroke="#22c55e" fillOpacity={1} fill="url(#colorOpt)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {savings > 0 && (
        <div style={{ marginTop: '20px', padding: '12px', background: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.3)', borderRadius: '6px' }}>
          <strong style={{ display: 'block', fontSize: '0.85rem', color: '#60a5fa', marginBottom: '4px' }}>Suggested Action</strong>
          <span style={{ fontSize: '0.85rem', color: '#e2e8f0', lineHeight: 1.4 }}>
            Shift flexible usage (up to 20%) from peak tariff hours (16:00-21:00) backward into standard or off-peak hours to match the optimized load curve mapped above.
          </span>
        </div>
      )}
    </div>
  );
}
