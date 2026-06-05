from pydantic import BaseModel


class LifePredictionRequest(
    BaseModel
):
    adult_mortality: float
    bmi: float
    gdp: float
    schooling: float
    population: float