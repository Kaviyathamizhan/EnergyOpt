from fastapi import APIRouter, Depends
from api.state import get_state
from api.schemas import Reading
from api.services.pipeline import run_predict, run_anomaly, run_optimize, update_buffer

router = APIRouter()

@router.post("/predict")
async def predict_only(request: Reading, state: dict = Depends(get_state)):
    """
    Returns only the forecast + confidence interval.
    """
    forecast_result = await run_predict(request, state)
    
    # Update buffer after forecast
    update_buffer(request, state)
    
    return forecast_result

@router.post("/predict_full")
async def predict_full(request: Reading, state: dict = Depends(get_state)):
    """
    Wrapper endpoint that orchestrates calls to predict, anomaly, and optimize.
    """
    # 1. Anomaly detection (before mutating buffer)
    anomaly_result = await run_anomaly(request, state)
    
    # 2. Forecast
    forecast_result = await run_predict(request, state)
    
    # 3. Update buffer for subsequent calls
    update_buffer(request, state)
    
    # 4. LP Optimization if requested
    optimize_result = None
    if request.run_optimizer:
        optimize_result = await run_optimize(forecast_result, state)
        
    return {
        "forecast": forecast_result,
        "anomaly": anomaly_result,
        "optimization": optimize_result
    }
