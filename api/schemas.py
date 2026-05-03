from pydantic import BaseModel, Field, field_validator
import numpy as np

class Reading(BaseModel):
    datetime: str = Field(
        ...,
        example="2007-01-01T18:00:00",
        description="ISO-8601 datetime of the reading"
    )
    consumption: float = Field(
        ..., ge=0.0, le=100.0, example=1.42,
        description="Global active power in kWh (0 to 100)"
    )
    run_optimizer: bool = Field(
        default=True,
        description="If true, run LP optimization"
    )

    @field_validator('consumption')
    @classmethod
    def consumption_must_be_finite(cls, v):
        if not np.isfinite(v):
            raise ValueError("consumption must be a finite number")
        return v

class BatchRequest(BaseModel):
    readings: list[Reading] = Field(..., min_length=1, max_length=168)
    
class OptimizeRequest(BaseModel):
    forecast_48h: list[float] = Field(..., min_length=48, max_length=48)
