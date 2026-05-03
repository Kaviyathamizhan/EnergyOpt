import numpy as np
from datetime import datetime
from fastapi import HTTPException
from src.optimization.lp_scheduler import optimize_window

# Schemas for internal return types if needed.
# For simplicity, we just return python dicts.

def _make_feature_array(features: dict, feature_columns: list) -> np.ndarray:
    ordered = [features[col] for col in feature_columns]
    return np.array(ordered, dtype=float).reshape(1, -1)

def _make_anomaly_array(anomaly_features: dict, anomaly_feature_columns: list) -> np.ndarray:
    ordered = [anomaly_features[col] for col in anomaly_feature_columns]
    return np.array(ordered, dtype=float).reshape(1, -1)

def _build_anomaly_severity(sigma_distance: float, ratio: float) -> str:
    if sigma_distance >= 6 or ratio >= 5:
        return "high"
    if sigma_distance >= 3.5 or ratio >= 2:
        return "medium"
    return "low"

async def run_predict(request, state: dict) -> dict:
    buf = state['buffer']
    dt = datetime.fromisoformat(request.datetime)
    
    # We must push to buffer BEFORE forecasting for the next step, according to previous flow?
    # Actually, previous flow: check anomaly BEFORE buffer, push buffer, then forecast.
    # Wait, the prompt says "run_predict" just returns forecast + interval.
    # So we don't mutate buffer in `run_predict`, we let the wrapper or something handle it?
    # "Do NOT recompute features here. Only orchestrate calls."
    # The buffer update needs to happen somewhere. Let's put buffer.add_reading inside `run_predict`, or does the wrapper do it? "All logic must exist ONLY inside run_* functions. Routers must not reimplement logic. Wrapper must not duplicate logic."
    
    if not buf.is_ready:
        raise HTTPException(status_code=503, detail="Buffer not ready")

    # In our old main.py, _run_forecast just read the buffer. It didn't push to it.
    features  = buf.get_forecast_features()
    X_raw     = _make_feature_array(features, state['feature_columns'])
    X_scaled  = state['scaler'].transform(X_raw)

    pred     = float(state['model'].predict(X_scaled)[0])
    pred_q05 = float(state['q05_model'].predict(X_scaled)[0])
    pred_q95 = float(state['q95_model'].predict(X_scaled)[0])

    pred     = max(0.0, pred)
    pred_q05 = max(0.0, pred_q05)
    pred_q95 = max(pred, max(0.0, pred_q95))

    return {
        'forecast_kWh': round(pred, 4),
        'confidence_interval': {
            'lower': round(pred_q05, 4),
            'upper': round(pred_q95, 4)
        }
    }

async def run_anomaly(request, state: dict) -> dict:
    buf = state['buffer']
    cfg = state['anomaly_config']
    consumption = request.consumption

    try:
        anomaly_features = buf.get_anomaly_features(consumption)
    except RuntimeError:
        return {
            'flag': False, 'severity': 'low',
            'stat_flag': False, 'iso_flag': False,
            'details': {'reason': 'insufficient_buffer'}
        }

    X_anom   = _make_anomaly_array(anomaly_features, state['anomaly_feature_columns'])
    iso_pred = state['iso_forest'].predict(X_anom)[0]
    iso_flag = (iso_pred == -1)

    mean24    = anomaly_features['rolling_mean_24h']
    std24     = anomaly_features['rolling_std_24h']
    sigma     = cfg.get('sigma_threshold', 3.5)
    abs_thr   = cfg.get('abs_threshold_kwh', 1.5)
    ratio_thr = cfg.get('ratio_threshold', 2.0)
    safe_mean = max(mean24, 0.01)

    cond_sigma = consumption > (mean24 + sigma * std24)
    cond_abs   = consumption > abs_thr
    cond_ratio = (consumption / safe_mean) > ratio_thr
    stat_flag  = cond_sigma and cond_abs and cond_ratio
    is_anomaly = stat_flag and iso_flag

    sigma_distance = round((consumption - mean24) / std24, 2) if std24 > 0 else 0.0
    ratio = round(consumption / safe_mean, 2)
    severity = _build_anomaly_severity(sigma_distance, ratio) if is_anomaly else "low"

    return {
        'flag': bool(is_anomaly),
        'severity': severity,
        'details': {
            'consumption':      round(consumption, 3),
            'rolling_mean_24h': round(mean24, 3),
            'rolling_std_24h':  round(std24, 3),
            'sigma_distance':   sigma_distance,
            'ratio':            ratio,
            'stat_flag':        bool(stat_flag),
            'iso_flag':         bool(iso_flag)
        }
    }

async def run_optimize(forecast_result: dict, state: dict) -> dict:
    if not forecast_result:
        return None

    # If the router passed a full 48-hour list directly (from /optimize endpoint)
    if 'forecast_48h' in forecast_result:
        profile_48h = forecast_result['forecast_48h']
    else:
        # Otherwise it's from /predict_full, where we just got 1-step forecast_kWh
        if forecast_result.get('forecast_kWh') is None:
            return None
        
        # Create a 48 hour naïve profile starting with our point forecast
        mean_baseline = state['buffer'].get_latest_consumption()
        horizon_hours = 48
        profile_48h   = [mean_baseline] * horizon_hours
        profile_48h[0] = forecast_result['forecast_kWh']
    
    optimizer_result = optimize_window(profile_48h)
    
    return optimizer_result

def update_buffer(request, state: dict):
    """Update global buffer."""
    dt = datetime.fromisoformat(request.datetime)
    state['buffer'].add_reading(dt, request.consumption)
