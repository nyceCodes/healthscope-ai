from datetime import datetime
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
    # Source metadata allows the UI to distinguish stored versus live-retrieved data.
    data_source: str = "unknown"
    data_as_of: datetime | None = None
    data_status: str = ""
