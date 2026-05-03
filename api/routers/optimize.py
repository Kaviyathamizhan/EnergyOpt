from fastapi import APIRouter, Depends
from api.schemas import OptimizeRequest
from api.state import get_state
from api.services.pipeline import run_optimize

router = APIRouter()

@router.post("/optimize")
async def optimize(request: OptimizeRequest, state: dict = Depends(get_state)):
    """
    Accepts 48-hour forecast input and returns optimized schedule using LP.
    We spoof a 'forecast_result' dict to reuse `run_optimize` logic cleanly.
    """
    # Create a spoofed forecast_result with actual data passing criteria
    # But wait, run_optimize creates its own 48-hour profile baseline using
    # mean_baseline = state['buffer'].get_latest_consumption()
    # Let's adjust `run_optimize` to take the profile directly if provided,
    # or handle it differently.
    
    # Actually, the user asked: "optimize endpoint receives 48 hour forecast input, calls run_optimize(), returns schedule."
    # So run_optimize shouldn't build the 48-hour list internally, it should accept the 48 hour list directly!
    # Let's import the raw optimize_window from lp_scheduler if we just want to run the raw optimizer,
    # or update run_optimize to handle this cleanly.
    
    # We will pass the 48h profile directly into run_optimize.
    optimize_result = await run_optimize({"forecast_48h": request.forecast_48h}, state)
    
    return optimize_result
