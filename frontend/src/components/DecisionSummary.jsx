import React from 'react';

/**
 * DecisionSummary
 * Translates model outputs into human-readable, factual business advice.
 */
export default function DecisionSummary({ forecast, anomaly, optimization, history }) {
  if (!forecast && !anomaly && !optimization) return null;

  const insights = [];

  // Anomaly Insights
  if (anomaly?.flag) {
    insights.push({
      type: 'critical',
      title: 'Anomaly Detected',
      text: 'Current consumption significantly deviated from expected rolling averages and historical baselines.'
    });
  } else if (anomaly) {
    insights.push({
      type: 'safe',
      title: 'Stable Operations',
      text: 'Current energy signature matches historical consumption patterns.'
    });
  }

  // Forecast Insights
  if (forecast?.forecast_kWh != null) {
    if (forecast.forecast_kWh > 3) { // Example threshold, simple factual statement
      insights.push({
        type: 'warning',
        title: 'High Load Anticipated',
        text: 'Short-term predictive models indicate elevated load.'
      });
    }
  }

  // Optimization Insights
  if (optimization?.savings > 0) {
    insights.push({
      type: 'action',
      title: 'Optimization Executed',
      text: `Algorithm successfully shifted peak-tier loads to less constrained off-peak periods, reducing localized cost by ${optimization.savings_pct?.toFixed(1)}%.`
    });
  }

  return (
    <div className="card">
      <h2 className="card-title">Decision Context</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '16px' }}>
        {insights.length > 0 ? (
          insights.map((insight, idx) => (
            <div 
              key={idx} 
              style={{
                padding: '12px',
                borderRadius: '6px',
                backgroundColor: 'rgba(30, 41, 59, 0.4)',
                borderLeft: `4px solid ${
                  insight.type === 'critical' ? '#ef4444' :
                  insight.type === 'safe' ? '#22c55e' :
                  insight.type === 'warning' ? '#f59e0b' : '#3b82f6'
                }`
              }}
            >
              <strong style={{ display: 'block', marginBottom: '4px', fontSize: '0.9rem', color: '#f8fafc' }}>
                {insight.title}
              </strong>
              <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>{insight.text}</span>
            </div>
          ))
        ) : (
          <p style={{ color: '#64748b', fontSize: '0.9rem' }}>Awaiting data to generate insights.</p>
        )}
      </div>
    </div>
  );
}
