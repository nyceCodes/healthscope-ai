from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.health_indicator import (
    HealthCountry,
    HealthDataSource,
    HealthIndicator,
    HealthIndicatorObservation,
)
from app.schemas.global_analytics import (
    ComparisonCountryRead,
    CountryComparisonRead,
    IndicatorRankingRead,
    RankingRowRead,
    TrendAnalysisRead,
    TrendSeriesRead,
)
from app.schemas.health_indicator import (
    HealthCountryRead,
    HealthIndicatorRead,
    HealthObservationRead,
)


def _country_read(country: HealthCountry) -> HealthCountryRead:
    return HealthCountryRead.model_validate(country)


def _indicator_read(
    indicator: HealthIndicator,
    source_name: str,
    latest_year: int | None,
) -> HealthIndicatorRead:
    return HealthIndicatorRead(
        code=indicator.code,
        name=indicator.name,
        definition=indicator.definition,
        unit=indicator.unit,
        source=source_name,
        latest_year=latest_year,
    )


def _observation_read(
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


def _metadata(db: Session, indicator: HealthIndicator) -> HealthIndicatorRead:
    source = db.get(HealthDataSource, indicator.source_code)
    if source is None:
        raise ValueError(f"Data source {indicator.source_code} is missing")
    latest_year = db.scalar(
        select(HealthIndicatorObservation.year)
        .where(HealthIndicatorObservation.indicator_code == indicator.code)
        .order_by(HealthIndicatorObservation.year.desc())
        .limit(1)
    )
    return _indicator_read(indicator, source.name, latest_year)


def _with_metadata(statement):
    return statement.options(
        joinedload(HealthIndicatorObservation.country),
        joinedload(HealthIndicatorObservation.indicator),
        joinedload(HealthIndicatorObservation.source),
    )


def build_trend_analysis(
    db: Session,
    iso3_codes: list[str],
    indicator: HealthIndicator,
    start_year: int,
    end_year: int,
) -> TrendAnalysisRead:
    countries = {
        country.iso3: country
        for country in db.scalars(
            select(HealthCountry).where(HealthCountry.iso3.in_(iso3_codes))
        )
    }
    observations = db.scalars(
        _with_metadata(select(HealthIndicatorObservation))
        .where(
            HealthIndicatorObservation.country_iso3.in_(iso3_codes),
            HealthIndicatorObservation.indicator_code == indicator.code,
            HealthIndicatorObservation.year.between(start_year, end_year),
        )
        .order_by(
            HealthIndicatorObservation.country_iso3,
            HealthIndicatorObservation.year,
        )
    ).all()
    grouped: dict[str, list[HealthObservationRead]] = {
        iso3: [] for iso3 in iso3_codes
    }
    for observation in observations:
        grouped[observation.country_iso3].append(
            _observation_read(observation)
        )

    series = []
    for iso3 in iso3_codes:
        rows = grouped[iso3]
        first = rows[0] if rows else None
        last = rows[-1] if rows else None
        has_interval = (
            first is not None
            and last is not None
            and first.year != last.year
        )
        change = last.value - first.value if has_interval else None
        percent_change = (
            change / first.value * 100
            if change is not None and first is not None and first.value != 0
            else None
        )
        country = countries[iso3]
        series.append(
            TrendSeriesRead(
                country=_country_read(country),
                observations=rows,
                change_from_year=first.year if has_interval and first else None,
                change_to_year=last.year if has_interval and last else None,
                absolute_change=change,
                percent_change=percent_change,
            )
        )

    return TrendAnalysisRead(
        indicator=_metadata(db, indicator),
        start_year=start_year,
        end_year=end_year,
        series=series,
    )


def build_country_comparison(
    db: Session,
    iso3_codes: list[str],
    indicator: HealthIndicator,
    year: int,
) -> CountryComparisonRead:
    countries = {
        country.iso3: country
        for country in db.scalars(
            select(HealthCountry).where(HealthCountry.iso3.in_(iso3_codes))
        )
    }
    observations = db.scalars(
        _with_metadata(select(HealthIndicatorObservation)).where(
            HealthIndicatorObservation.country_iso3.in_(iso3_codes),
            HealthIndicatorObservation.indicator_code == indicator.code,
            HealthIndicatorObservation.year == year,
        )
    ).all()
    by_country = {row.country_iso3: row for row in observations}
    reference = by_country.get(iso3_codes[0])
    results = []
    for iso3 in iso3_codes:
        observation = by_country.get(iso3)
        difference = (
            observation.value - reference.value
            if observation is not None and reference is not None
            else None
        )
        percent_difference = (
            difference / reference.value * 100
            if difference is not None and reference is not None and reference.value != 0
            else None
        )
        results.append(
            ComparisonCountryRead(
                country=_country_read(countries[iso3]),
                observation=(
                    _observation_read(observation)
                    if observation is not None
                    else None
                ),
                difference_from_reference=difference,
                percent_difference_from_reference=percent_difference,
            )
        )

    return CountryComparisonRead(
        indicator=_metadata(db, indicator),
        year=year,
        reference_iso3=iso3_codes[0],
        countries=results,
    )


def build_indicator_ranking(
    db: Session,
    indicator: HealthIndicator,
    year: int,
    order: Literal["ascending", "descending"],
) -> IndicatorRankingRead:
    ordering = (
        HealthIndicatorObservation.value.asc()
        if order == "ascending"
        else HealthIndicatorObservation.value.desc()
    )
    observations = db.scalars(
        _with_metadata(select(HealthIndicatorObservation))
        .where(
            HealthIndicatorObservation.indicator_code == indicator.code,
            HealthIndicatorObservation.year == year,
        )
        .order_by(ordering, HealthIndicatorObservation.country_iso3)
    ).all()
    rows = [
        RankingRowRead(rank=index, observation=_observation_read(observation))
        for index, observation in enumerate(observations, start=1)
    ]
    return IndicatorRankingRead(
        indicator=_metadata(db, indicator),
        year=year,
        order=order,
        rows=rows,
    )
