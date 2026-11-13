from datetime import datetime

from pydantic import BaseModel, ConfigDict


class HealthCountryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    iso3: str
    iso2: str | None
    name: str
    region: str | None
    income_level: str | None


class HealthIndicatorRead(BaseModel):
    code: str
    name: str
    definition: str
    unit: str
    source: str
    latest_year: int | None


class HealthObservationRead(BaseModel):
    country_iso3: str
    country_name: str
    indicator_code: str
    indicator_name: str
    value: float
    year: int
    unit: str
    source: str
    imported_at: datetime


class HealthObservationSet(BaseModel):
    indicator: HealthIndicatorRead
    year: int | None
    observations: list[HealthObservationRead]


class HealthCountryObservationSet(BaseModel):
    country: HealthCountryRead
    observations: list[HealthObservationRead]
