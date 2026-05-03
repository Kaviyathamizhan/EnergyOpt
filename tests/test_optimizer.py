import pytest
import numpy as np
from src.optimization.lp_scheduler import optimize_window

def test_optimize_window_basic():
    """
    Ensure the LP optimizer successfully shifts load and maintains total energy conservation.
    """
    # Create a 48 hour synthetic forecast profile with high peak load
    # Peak hours are 16..20 (indices 16, 17, 18, 19, 20) and (40, 41, 42, 43, 44)
    forecast = [1.5] * 48
    for h in [16, 17, 18, 19, 20, 40, 41, 42, 43, 44]:
        forecast[h] = 3.0
        
    result = optimize_window(forecast, flexibility_pct=0.20)
    
    assert result['solver_status'] == 'optimal', "Solver failed to find an optimal solution."
    
    # Assert optimized cost is less than or equal to original cost
    assert result['optimized_cost'] <= result['original_cost'], "Optimization did not reduce or maintain cost."
    
    # Assert energy conservation: sum(optimized) ≈ sum(original)
    original_sum = sum(result['original_profile'])
    optimized_sum = sum(result['optimized_profile'])
    assert np.isclose(original_sum, optimized_sum, atol=1e-3), "Total energy payload was not conserved during the shift."

    # Assert bounded flexibility (max 20% shift on any hour)
    for orig, opt in zip(result['original_profile'], result['optimized_profile']):
        assert opt >= orig * 0.799, f"Load shifted too far down: {opt} vs {orig}"
        assert opt <= orig * 1.201, f"Load shifted too far up: {opt} vs {orig}"
