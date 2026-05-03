from fastapi import APIRouter, Depends
from api.state import get_state
from api.schemas import Reading
from api.services.pipeline import run_anomaly

router = APIRouter()

@router.post("/anomaly")
async def anomaly(request: Reading, state: dict = Depends(get_state)):
    """
    Evaluates anomaly using Isolation Forest and Statistical Gates.
    Does NOT update the buffer.
    """
    anomaly_result = await run_anomaly(request, state)
    return anomaly_result
