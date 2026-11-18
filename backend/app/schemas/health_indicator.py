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
    publisher: str | None = None
    definition_url: str | None = None
    dataset_code: str | None = None
    dataset_name: str | None = None
    dataset_version: str | None = None


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
    source_reference: str | None = None
    source_publication_date: datetime | None = None
    source_record_timestamp: datetime | None = None
    source_value_text: str | None = None
    denominator_value: float | None = None
    denominator_definition: str | None = None
    dimensions: dict[str, str] | None = None
    uncertainty_lower: float | None = None
    uncertainty_upper: float | None = None
    estimate_status: str | None = None


class HealthObservationSet(BaseModel):
    indicator: HealthIndicatorRead
    year: int | None
    observations: list[HealthObservationRead]


class HealthCountryObservationSet(BaseModel):
    country: HealthCountryRead
    observations: list[HealthObservationRead]


class HealthDataCoverageRead(BaseModel):
    indicator_code: str
    country_iso3: str
    country_name: str
    observation_count: int
    first_year: int
    last_year: int
    observed_years: list[int]
    unobserved_years_within_span: list[int]
    cadence_note: str
