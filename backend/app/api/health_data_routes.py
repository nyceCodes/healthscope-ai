from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Literal
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.database.session import get_db
from app.models.health_indicator import (
    HealthCountry,
    HealthDataSource,
    HealthIndicator,
    HealthIndicatorObservation,
)
from app.schemas.health_indicator import (
    HealthCountryObservationSet,
    HealthCountryRead,
    HealthIndicatorRead,
    HealthObservationRead,
    HealthObservationSet,
)
from app.schemas.global_analytics import (
    CountryComparisonRead,
    IndicatorRankingRead,
    TrendAnalysisRead,
)
from app.services.global_analytics_service import (
    build_country_comparison,
    build_indicator_ranking,
    build_trend_analysis,
)

router = APIRouter()


def _country_response(country: HealthCountry) -> HealthCountryRead:
    return HealthCountryRead.model_validate(country)


def _indicator_response(db: Session, indicator: HealthIndicator) -> HealthIndicatorRead:
    latest_year = db.scalar(
        select(func.max(HealthIndicatorObservation.year)).where(
            HealthIndicatorObservation.indicator_code == indicator.code
        )
    )
    source = db.get(HealthDataSource, indicator.source_code)
    if source is None:
        raise HTTPException(status_code=500, detail="Indicator data source is missing")
    return HealthIndicatorRead(
        code=indicator.code,
        name=indicator.name,
        definition=indicator.definition,
        unit=indicator.unit,
        source=source.name,
        latest_year=latest_year,
    )


def _observation_response(
    observation: HealthIndicatorObservation,
) -> HealthObservationRead:
    return HealthObservationRead(
        country_iso3=observation.country.iso3,
        country_name=observation.country.name,
        indicator_code=observation.indicator.code,
        indicator_name=observation.indicator.name,
        value=observation.value,
        year=observation.year,
        unit=observation.unit,
        source=observation.source.name,
        imported_at=observation.imported_at,
    )


def _with_observation_metadata(statement):
    return statement.options(
        joinedload(HealthIndicatorObservation.country),
        joinedload(HealthIndicatorObservation.indicator),
        joinedload(HealthIndicatorObservation.source),
    )


def _get_indicator(db: Session, code: str) -> HealthIndicator:
    indicator = db.get(HealthIndicator, code)
    if indicator is None:
        raise HTTPException(status_code=404, detail="Indicator not found")
    return indicator


@router.get("/countries", response_model=list[HealthCountryRead])
def list_health_countries(db: Session = Depends(get_db)) -> list[HealthCountryRead]:
    countries = db.scalars(
        select(HealthCountry).order_by(HealthCountry.name)
    ).all()
    return [_country_response(country) for country in countries]


@router.get("/indicators", response_model=list[HealthIndicatorRead])
def list_health_indicators(db: Session = Depends(get_db)) -> list[HealthIndicatorRead]:
    indicators = db.scalars(
        select(HealthIndicator).order_by(HealthIndicator.name)
    ).all()
    return [_indicator_response(db, indicator) for indicator in indicators]


@router.get(
    "/indicators/{indicator_code}/years",
    response_model=list[int],
)
def list_indicator_years(
    indicator_code: str,
    db: Session = Depends(get_db),
) -> list[int]:
    _get_indicator(db, indicator_code)
    return list(
        db.scalars(
            select(HealthIndicatorObservation.year)
            .where(HealthIndicatorObservation.indicator_code == indicator_code)
            .distinct()
            .order_by(HealthIndicatorObservation.year.desc())
        )
    )


@router.get(
    "/indicators/{indicator_code}/observations",
    response_model=HealthObservationSet,
)
def list_indicator_observations(
    indicator_code: str,
    year: int | None = Query(default=None, ge=1900, le=2100),
    db: Session = Depends(get_db),
) -> HealthObservationSet:
    indicator = _get_indicator(db, indicator_code)
    selected_year = year
    if selected_year is None:
        selected_year = db.scalar(
            select(func.max(HealthIndicatorObservation.year)).where(
                HealthIndicatorObservation.indicator_code == indicator_code
            )
        )
    if selected_year is None:
        return HealthObservationSet(
            indicator=_indicator_response(db, indicator),
            year=None,
            observations=[],
        )

    observations = db.scalars(
        _with_observation_metadata(select(HealthIndicatorObservation))
        .where(
            HealthIndicatorObservation.indicator_code == indicator_code,
            HealthIndicatorObservation.year == selected_year,
        )
        .order_by(HealthIndicatorObservation.country_iso3)
    ).all()
    return HealthObservationSet(
        indicator=_indicator_response(db, indicator),
        year=selected_year,
        observations=[
            _observation_response(observation) for observation in observations
        ],
    )


@router.get(
    "/countries/{iso3}/observations",
    response_model=HealthCountryObservationSet,
)
def list_country_observations(
    iso3: str,
    year: int | None = Query(default=None, ge=1900, le=2100),
    db: Session = Depends(get_db),
) -> HealthCountryObservationSet:
    country = db.get(HealthCountry, iso3.strip().upper())
    if country is None:
        raise HTTPException(status_code=404, detail="Country not found")
    statement = select(HealthIndicatorObservation).where(
        HealthIndicatorObservation.country_iso3 == country.iso3
    )
    if year is not None:
        statement = statement.where(HealthIndicatorObservation.year == year)
    observations = db.scalars(
        _with_observation_metadata(statement).order_by(
            HealthIndicatorObservation.year.desc(),
            HealthIndicatorObservation.indicator_code,
        )
    ).all()
    return HealthCountryObservationSet(
        country=_country_response(country),
        observations=[
            _observation_response(observation) for observation in observations
        ],
    )


@router.get(
    "/countries/{iso3}/indicators/{indicator_code}/history",
    response_model=list[HealthObservationRead],
)
def country_indicator_history(
    iso3: str,
    indicator_code: str,
    db: Session = Depends(get_db),
) -> list[HealthObservationRead]:
    country = db.get(HealthCountry, iso3.strip().upper())
    if country is None:
        raise HTTPException(status_code=404, detail="Country not found")
    _get_indicator(db, indicator_code)
    observations = db.scalars(
        _with_observation_metadata(select(HealthIndicatorObservation))
        .where(
            HealthIndicatorObservation.country_iso3 == country.iso3,
            HealthIndicatorObservation.indicator_code == indicator_code,
        )
        .order_by(HealthIndicatorObservation.year)
    ).all()
    return [
        _observation_response(observation) for observation in observations
    ]


def _normalize_analytics_countries(
    countries: list[str],
    minimum: int,
    maximum: int,
) -> list[str]:
    normalized = [country.strip().upper() for country in countries]
    if not minimum <= len(normalized) <= maximum:
        raise HTTPException(
            status_code=422,
            detail=f"Select between {minimum} and {maximum} countries",
        )
    if any(len(country) != 3 or not country.isalpha() for country in normalized):
        raise HTTPException(status_code=422, detail="Countries must use ISO-3 codes")
    if len(set(normalized)) != len(normalized):
        raise HTTPException(status_code=422, detail="Countries must be unique")
    return normalized


def _validate_analytics_countries(
    db: Session,
    countries: list[str],
    minimum: int,
    maximum: int,
) -> list[str]:
    normalized = _normalize_analytics_countries(countries, minimum, maximum)
    existing = set(
        db.scalars(
            select(HealthCountry.iso3).where(HealthCountry.iso3.in_(normalized))
        )
    )
    missing = [country for country in normalized if country not in existing]
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown country ISO-3 code(s): {', '.join(missing)}",
        )
    return normalized


@router.get("/analytics/trends", response_model=TrendAnalysisRead)
def indicator_trends(
    indicator_code: str,
    countries: list[str] = Query(...),
    start_year: int = Query(..., ge=1900, le=2100),
    end_year: int = Query(..., ge=1900, le=2100),
    db: Session = Depends(get_db),
) -> TrendAnalysisRead:
    if start_year > end_year:
        raise HTTPException(
            status_code=422,
            detail="start_year must be less than or equal to end_year",
        )
    country_codes = _validate_analytics_countries(db, countries, 1, 5)
    indicator = _get_indicator(db, indicator_code)
    return build_trend_analysis(
        db, country_codes, indicator, start_year, end_year
    )


@router.get("/analytics/compare", response_model=CountryComparisonRead)
def compare_health_indicators(
    indicator_code: str,
    year: int = Query(..., ge=1900, le=2100),
    countries: list[str] = Query(...),
    db: Session = Depends(get_db),
) -> CountryComparisonRead:
    country_codes = _validate_analytics_countries(db, countries, 2, 5)
    indicator = _get_indicator(db, indicator_code)
    return build_country_comparison(db, country_codes, indicator, year)


@router.get("/analytics/rankings", response_model=IndicatorRankingRead)
def indicator_rankings(
    indicator_code: str,
    year: int = Query(..., ge=1900, le=2100),
    order: Literal["ascending", "descending"] = "descending",
    db: Session = Depends(get_db),
) -> IndicatorRankingRead:
    indicator = _get_indicator(db, indicator_code)
    return build_indicator_ranking(db, indicator, year, order)
