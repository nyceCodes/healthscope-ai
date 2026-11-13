from pydantic import BaseModel, Field


class LifePredictionRequest(BaseModel):
    adult_mortality: float = Field(ge=0, allow_inf_nan=False)
    bmi: float = Field(gt=0, allow_inf_nan=False)
    gdp: float = Field(ge=0, allow_inf_nan=False)
    schooling: float = Field(ge=0, allow_inf_nan=False)
    population: float = Field(gt=0, allow_inf_nan=False)