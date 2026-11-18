from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.health_indicator import HealthCountry, HealthIndicatorObservation
from app.schemas.health_indicator import HealthDataCoverageRead


def build_data_coverage(
    db: Session,
    indicator_code: str | None = None,
    country_iso3: str | None = None,
) -> list[HealthDataCoverageRead]:
    statement = (
        select(
            HealthIndicatorObservation.indicator_code,
            HealthIndicatorObservation.country_iso3,
            HealthCountry.name,
            HealthIndicatorObservation.year,
        )
        .join(
            HealthCountry,
            HealthCountry.iso3 == HealthIndicatorObservation.country_iso3,
        )
        .order_by(
            HealthIndicatorObservation.indicator_code,
            HealthIndicatorObservation.country_iso3,
            HealthIndicatorObservation.year,
        )
    )
    if indicator_code is not None:
        statement = statement.where(
            HealthIndicatorObservation.indicator_code == indicator_code
        )
    if country_iso3 is not None:
        statement = statement.where(
            HealthIndicatorObservation.country_iso3 == country_iso3
        )

    grouped: dict[tuple[str, str], tuple[str, list[int]]] = {}
    for code, iso3, name, year in db.execute(statement):
        key = (code, iso3)
        if key not in grouped:
            grouped[key] = (name, [])
        grouped[key][1].append(year)

    result = []
    for (code, iso3), (name, years) in grouped.items():
        observed_years = sorted(set(years))
        first_year = observed_years[0]
        last_year = observed_years[-1]
        observed_set = set(observed_years)
        result.append(
            HealthDataCoverageRead(
                indicator_code=code,
                country_iso3=iso3,
                country_name=name,
                observation_count=len(years),
                first_year=first_year,
                last_year=last_year,
                observed_years=observed_years,
                unobserved_years_within_span=[
                    year
                    for year in range(first_year, last_year + 1)
                    if year not in observed_set
                ],
                cadence_note=(
                    "Unobserved years do not imply an expected annual report; "
                    "cadence is indicator- and source-specific."
                ),
            )
        )
    return result
