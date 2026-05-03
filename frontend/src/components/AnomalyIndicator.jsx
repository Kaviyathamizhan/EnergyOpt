import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';

const SEVERITY_COLOR = { low: '#22c55e', medium: '#f59e0b', high: '#ef4444' };
const SEVERITY_LABEL = { low: 'Normal', medium: 'Warning', high: 'Anomaly' };

// Custom dot renderer for plotting anomalies
const AnomalyDot = (props) => {
  const { cx, cy, payload } = props;
  if (!cx || !cy) return null;

  if (payload.anomaly) {
    return (
      <circle cx={cx} cy={cy} r={5} fill="#ef4444" stroke="#7f1d1d" strokeWidth={2} />
    );
  }
  return (
    <circle cx={cx} cy={cy} r={3} fill="#22c55e" />
  );
};

export default function AnomalyIndicator({ anomaly, history = [] }) {
  if (!anomaly && history.length === 0) return null;

  const severity  = anomaly?.flag ? (anomaly.severity || 'medium') : 'low';
  const color     = SEVERITY_COLOR[severity];
  const label     = anomaly?.flag ? SEVERITY_LABEL[severity] : 'Normal';

  return (
    <div className="card anomaly-card">
      <h2 className="card-title">Anomaly Monitoring</h2>

      {anomaly && (
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center', marginBottom: '20px' }}>
          <div className="anomaly-badge" style={{ backgroundColor: color, flexShrink: 0 }}>
            <span className="badge-icon">{anomaly.flag ? '⚠' : '✓'}</span>
            <span className="badge-label">{label}</span>
          </div>
          <p style={{ margin: 0, fontSize: '0.85rem', color: '#94a3b8', lineHeight: 1.4 }}>
            Distance: <strong>{anomaly.details?.sigma_distance ?? '—'} σ</strong> |
            Ratio: <strong>{anomaly.details?.ratio ?? '—'}x</strong>
          </p>
        </div>
      )}

      {/* FULL SESSION TIMELINE VIEW */}
      {history.length > 0 && (
        <div className="anomaly-timeline" style={{ borderTop: '1px solid #1e293b', paddingTop: '16px' }}>
          <h3 style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '12px' }}>Historical Session Tracker</h3>
          <ResponsiveContainer width="100%" height={150}>
            <LineChart data={history} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="label" tick={{ fill: '#64748b', fontSize: 10 }} />
              <YAxis unit=" kWh" tick={{ fill: '#64748b', fontSize: 10 }} />
              <Tooltip 
                contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8, fontSize: '0.8rem' }}
                formatter={(value, name, props) => [
                  `${value} kWh ${props.payload.anomaly ? '(ANOMALY)' : ''}`, 
                  'Load'
                ]}
              />
              <Line 
                type="monotone" 
                dataKey="actual" 
                stroke="#64748b" 
                strokeWidth={2}
                dot={<AnomalyDot />} 
                activeDot={{ r: 6 }} 
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
