from typing import Literal

from pydantic import BaseModel

from app.schemas.health_indicator import (
    HealthCountryRead,
    HealthIndicatorRead,
    HealthObservationRead,
)


class TrendSeriesRead(BaseModel):
    country: HealthCountryRead
    observations: list[HealthObservationRead]
    change_from_year: int | None
    change_to_year: int | None
    absolute_change: float | None
    percent_change: float | None


class TrendAnalysisRead(BaseModel):
    indicator: HealthIndicatorRead
    start_year: int
    end_year: int
    series: list[TrendSeriesRead]


class ComparisonCountryRead(BaseModel):
    country: HealthCountryRead
    observation: HealthObservationRead | None
    difference_from_reference: float | None
    percent_difference_from_reference: float | None


class CountryComparisonRead(BaseModel):
    indicator: HealthIndicatorRead
    year: int
    reference_iso3: str
    countries: list[ComparisonCountryRead]


class RankingRowRead(BaseModel):
    rank: int
    observation: HealthObservationRead


class IndicatorRankingRead(BaseModel):
    indicator: HealthIndicatorRead
    year: int
    order: Literal["ascending", "descending"]
    rows: list[RankingRowRead]
