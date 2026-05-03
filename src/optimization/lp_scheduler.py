"""
LP Optimizer: Energy Load-Shifting via Linear Programming
=========================================================
Single source of truth for LP scheduling logic.
"""
import numpy as np
from scipy.optimize import linprog

# ---- Default Residential TOU Tariff (Rs./kWh) ----
TARIFF = {
    'peak_hours': list(range(16, 21)),
    'mid_peak_hours': list(range(7, 16)),
    'off_peak_hours': list(range(0, 7)) + list(range(21, 24)),
    'peak_rate': 9.0,
    'mid_peak_rate': 6.5,
    'off_peak_rate': 3.5,
}

def build_tariff_vector(tariff: dict = None, horizon: int = 48) -> np.ndarray:
    """Build a rate vector spanning `horizon` hours."""
    if tariff is None:
        tariff = TARIFF
    rates = np.full(horizon, tariff['mid_peak_rate'])
    for h in range(horizon):
        hour_of_day = h % 24
        if hour_of_day in tariff['peak_hours']:
            rates[h] = tariff['peak_rate']
        elif hour_of_day in tariff['off_peak_hours']:
            rates[h] = tariff['off_peak_rate']
    return rates

def optimize_window(
    forecast_horizon: list,
    flexibility_pct: float = 0.20,
    tariff: dict = None,
) -> dict:
    """
    Optimize an energy profile by shifting flexible load to cheaper hours.
    
    Returns a dict with schedules and cost savings.
    """
    forecast = np.array(forecast_horizon, dtype=float)
    horizon_len = len(forecast)
    
    rates = build_tariff_vector(tariff, horizon=horizon_len)

    c     = rates
    A_eq  = np.ones((1, horizon_len))
    b_eq  = np.array([forecast.sum()])

    bounds = []
    for h in range(horizon_len):
        lower = max(0.0, forecast[h] * (1 - flexibility_pct))
        upper = forecast[h] * (1 + flexibility_pct)
        bounds.append((lower, upper))

    # Solve the linear program
    result = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')

    if not result.success:
        orig_cost = float(np.dot(forecast, rates))
        return {
            'original_profile': forecast.tolist(),
            'optimized_profile': forecast.tolist(),
            'original_cost': orig_cost,
            'optimized_cost': orig_cost,
            'savings': 0.0,
            'savings_pct': 0.0,
            'solver_status': 'failed',
        }

    optimized      = result.x
    original_cost  = float(np.dot(forecast, rates))
    optimized_cost = float(np.dot(optimized, rates))
    savings        = original_cost - optimized_cost

    return {
        'original_profile': [round(float(v), 3) for v in forecast],
        'optimized_profile': [round(float(v), 3) for v in optimized],
        'original_cost':  round(original_cost, 2),
        'optimized_cost': round(optimized_cost, 2),
        'savings':        round(savings, 2),
        'savings_pct':    round(savings / original_cost * 100, 1) if original_cost > 0 else 0.0,
        'solver_status':  'optimal',
    }
