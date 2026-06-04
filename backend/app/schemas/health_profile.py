from pydantic import BaseModel

class HealthProfile(BaseModel):

    country: str

    population: int

    region: str

    capital: str

    cases: int

    deaths: int

    recovered: int

    active: int

    tests: int

    recovery_rate: float

    mortality_rate: float

    health_index: float