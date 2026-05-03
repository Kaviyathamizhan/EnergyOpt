import React, { useState } from 'react';

/**
 * PredictionForm — Input fields for timestamp + consumption.
 * Calls onSubmit(datetime, consumption, runOptimizer).
 */
export default function PredictionForm({ onSubmit, loading }) {
  const [datetime, setDatetime] = useState('2007-01-15T18:00:00');
  const [consumption, setConsumption] = useState('1.42');
  const [runOptimizer, setRunOptimizer] = useState(true);
  const [error, setError] = useState('');

  function handleSubmit(e) {
    e.preventDefault();
    setError('');
    const c = parseFloat(consumption);
    if (isNaN(c) || c < 0 || c > 100) {
      setError('Consumption must be a number between 0 and 100 kWh.');
      return;
    }
    onSubmit(datetime, c, runOptimizer);
  }

  return (
    <form className="card prediction-form" onSubmit={handleSubmit}>
      <h2 className="card-title">New Reading</h2>

      <div className="form-row">
        <label>Timestamp (ISO-8601)</label>
        <input
          type="datetime-local"
          step="3600"
          value={datetime.slice(0, 16)}
          onChange={e => setDatetime(e.target.value + ':00')}
          required
        />
      </div>

      <div className="form-row">
        <label>Consumption (kWh)</label>
        <input
          type="number"
          min="0" max="100" step="0.01"
          value={consumption}
          onChange={e => setConsumption(e.target.value)}
          required
        />
      </div>

      <div className="form-row form-check">
        <label>
          <input
            type="checkbox"
            checked={runOptimizer}
            onChange={e => setRunOptimizer(e.target.checked)}
          />
          &nbsp;Run LP Cost Optimizer
        </label>
      </div>

      {error && <p className="form-error">{error}</p>}

      <button type="submit" className="btn-primary" disabled={loading}>
        {loading ? 'Running...' : 'Submit Reading'}
      </button>
    </form>
  );
}
