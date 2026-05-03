/**
 * api.js — Backend API calls
 * All calls go to http://127.0.0.1:8000
 */
import axios from 'axios';

const BASE = 'http://127.0.0.1:8000';

const api = axios.create({ baseURL: BASE, timeout: 10000 });

/**
 * POST /predict
 * @param {string} datetime  ISO-8601 string
 * @param {number} consumption kWh
 * @param {boolean} runOptimizer
 */
export async function predict(datetime, consumption, runOptimizer = true) {
  const { data } = await api.post('/predict_full', {
    datetime,
    consumption: parseFloat(consumption),
    run_optimizer: runOptimizer,
  });
  return data;
}

/**
 * GET /health
 */
export async function getHealth() {
  const { data } = await api.get('/health');
  return data;
}

/**
 * GET /buffer/status
 */
export async function getBufferStatus() {
  const { data } = await api.get('/buffer/status');
  return data;
}
