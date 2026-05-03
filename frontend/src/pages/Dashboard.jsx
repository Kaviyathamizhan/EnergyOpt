import React, { useState, useEffect, useCallback } from 'react';
import PredictionForm from '../components/PredictionForm';
import ForecastChart from '../components/ForecastChart';
import AnomalyIndicator from '../components/AnomalyIndicator';
import OptimizationPanel from '../components/OptimizationPanel';
import DecisionSummary from '../components/DecisionSummary';
import { predict, getHealth } from '../services/api';

const MAX_HISTORY = 24; // keep last 24 readings on the chart

export default function Dashboard() {
  const [loading, setLoading]           = useState(false);
  const [error, setError]               = useState('');
  const [apiStatus, setApiStatus]       = useState(null);
  const [lastResult, setLastResult]     = useState(null);
  const [history, setHistory]           = useState([]);       // for chart

  // Check backend health on mount
  useEffect(() => {
    getHealth()
      .then(h => setApiStatus(h))
      .catch(() => setApiStatus({ status: 'unreachable' }));
  }, []);

  const handleSubmit = useCallback(async (datetime, consumption, runOptimizer) => {
    setLoading(true);
    setError('');
    try {
      const result = await predict(datetime, consumption, runOptimizer);
      setLastResult(result);

      // Append to history for the chart
      const label = datetime.slice(11, 16); // HH:MM
      setHistory(prev => {
        const entry = {
          label,
          actual:   consumption,
          forecast: result.forecast?.forecast_kWh,
          q05:      result.forecast?.confidence_interval?.lower,
          q95:      result.forecast?.confidence_interval?.upper,
          anomaly:  result.anomaly?.flag,
        };
        const next = [...prev, entry];
        return next.length > MAX_HISTORY ? next.slice(-MAX_HISTORY) : next;
      });
    } catch (err) {
      const detail = err.response?.data?.detail || err.message || 'Unknown error';
      setError(`API Error: ${detail}`);
    } finally {
      setLoading(false);
    }
  }, []);

  // Status badge
  const statusColor = {
    ok: '#22c55e',
    unreachable: '#ef4444',
  }[apiStatus?.status] ?? '#f59e0b';

  return (
    <div className="dashboard">
      {/* ── Header ── */}
      <header className="dash-header">
        <div className="header-left">
          <h1 className="dash-title">Energy Decision Dashboard</h1>
          <p className="dash-subtitle">LightGBM Forecast · Anomaly Detection · LP Optimization</p>
        </div>
        <div className="header-right">
          {apiStatus && (
            <div className="status-pill" style={{ borderColor: statusColor }}>
              <span className="status-dot" style={{ backgroundColor: statusColor }} />
              <span>
                {apiStatus.status === 'ok'
                  ? `API Online · ${apiStatus.model} · RMSE ${apiStatus.test_rmse}`
                  : 'API Unreachable'}
              </span>
            </div>
          )}
        </div>
      </header>

      {/* ── Error Banner ── */}
      {error && <div className="error-banner">{error}</div>}

      {/* ── Workflow Explanation Banner ── */}
      <div className="card" style={{ marginBottom: '24px', backgroundColor: 'rgba(30, 41, 59, 0.4)', padding: '16px' }}>
        <h3 style={{ fontSize: '0.9rem', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '12px' }}>AI Pipeline Workflow</h3>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontWeight: '500', color: '#e2e8f0', fontSize: '0.95rem' }}>
          <div style={{ textAlign: 'center', flex: 1 }}>
            <span style={{ display: 'block', fontSize: '1.2rem', marginBottom: '4px' }}>📥</span>
            1. User inputs a single hourly reading
          </div>
          <div style={{ color: '#cbd5e1' }}>→</div>
          <div style={{ textAlign: 'center', flex: 1 }}>
            <span style={{ display: 'block', fontSize: '1.2rem', marginBottom: '4px' }}>🧠</span>
            2. AI projects bounds over 48 hours
          </div>
          <div style={{ color: '#cbd5e1' }}>→</div>
          <div style={{ textAlign: 'center', flex: 1 }}>
            <span style={{ display: 'block', fontSize: '1.2rem', marginBottom: '4px' }}>⚡</span>
            3. LP Optimizer shifts peak schedules
          </div>
        </div>
      </div>

      {/* ── Main Layout ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        
        {/* Column 1: Forecast & Operations */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          <section className="dashboard-section">
            <h3 style={{ borderBottom: '1px solid #334155', paddingBottom: '8px', marginBottom: '16px', color: '#cbd5e1' }}>
              1. Forecast & Confidence
            </h3>
            <PredictionForm onSubmit={handleSubmit} loading={loading} />
            
            {lastResult && (
              <div className="card forecast-summary-card" style={{ marginTop: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h2 className="card-title" style={{ margin: 0 }}>Target Prediction</h2>
                  <div className="forecast-value" style={{ margin: 0, fontSize: '1.25rem' }}>
                    {lastResult.forecast?.forecast_kWh != null ? lastResult.forecast.forecast_kWh.toFixed(4) : '—'}
                    <span className="forecast-unit" style={{ fontSize: '0.9rem' }}> kWh</span>
                  </div>
                </div>
                {lastResult.forecast?.confidence_interval?.lower != null && (
                  <p className="ci-text" style={{ marginTop: '8px' }}>
                    90% CI: [{lastResult.forecast.confidence_interval.lower.toFixed(3)},&nbsp;
                    {lastResult.forecast.confidence_interval.upper.toFixed(3)}] kWh
                  </p>
                )}
                <p className="meta-text">
                  Model: {lastResult.metadata?.algorithm} · Buffer: {lastResult.metadata?.buffer_rows} rows
                </p>
              </div>
            )}
            
            <div style={{ marginTop: '16px' }}>
              <ForecastChart history={history} />
            </div>
          </section>

          <section className="dashboard-section">
            <h3 style={{ borderBottom: '1px solid #334155', paddingBottom: '8px', marginBottom: '16px', color: '#cbd5e1' }}>
              2. Anomaly Monitoring
            </h3>
            <AnomalyIndicator anomaly={lastResult?.anomaly} history={history} />
          </section>

        </div>

        {/* Column 2: Insights & Strategy */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          <section className="dashboard-section">
            <h3 style={{ borderBottom: '1px solid #334155', paddingBottom: '8px', marginBottom: '16px', color: '#cbd5e1' }}>
              3. Optimization Insights
            </h3>
            <DecisionSummary 
              forecast={lastResult?.forecast} 
              anomaly={lastResult?.anomaly} 
              optimization={lastResult?.optimization} 
              history={history} 
            />
            <div style={{ marginTop: '16px' }}>
              <OptimizationPanel optimization={lastResult?.optimization} />
            </div>
          </section>

        </div>
      </div>
    </div>
  );
}
