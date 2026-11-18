import json
from fastapi import FastAPI
from fastapi.testclient import TestClient
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.health_data_routes import router
from app.database.database import Base
from app.database.session import get_db
from app.models.health_indicator import (
    HealthCountry,
    HealthDataSource,
    HealthIndicator,
    HealthIndicatorObservation,
)


def make_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as db:
        db.add(
            HealthCountry(
                iso3="PHL",
                iso2="PH",
                name="Philippines",
                region="East Asia & Pacific",
                income_level="Lower middle income",
            )
        )
        db.add(
            HealthDataSource(
                code="world-bank-wdi",
                name="World Bank — World Development Indicators",
                url="https://api.worldbank.org/v2",
            )
        )
        db.add(
            HealthIndicator(
                code="SP.DYN.LE00.IN",
                name="Life expectancy at birth, total (years)",
                definition="Years a newborn is expected to live under current mortality patterns.",
                unit="years",
                source_code="world-bank-wdi",
            )
        )
        db.flush()
        db.add_all(
            [
                HealthIndicatorObservation(
                    country_iso3="PHL",
                    indicator_code="SP.DYN.LE00.IN",
                    year=2020,
                    value=71.2,
                    unit="years",
                    source_code="world-bank-wdi",
                ),
                HealthIndicatorObservation(
                    country_iso3="PHL",
                    indicator_code="SP.DYN.LE00.IN",
                    year=2021,
                    value=71.5,
                    unit="years",
                    source_code="world-bank-wdi",
                ),
            ]
        )
        db.commit()

    app = FastAPI()

    def override_get_db():
        with session_factory() as db:
            yield db

    app.include_router(router, prefix="/health/data")
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), engine


def test_indicator_endpoints_include_year_source_and_country_metadata():
    client, engine = make_client()
    try:
        indicators = client.get("/health/data/indicators")
        assert indicators.status_code == 200
        assert indicators.json()[0]["latest_year"] == 2021

        years = client.get("/health/data/indicators/SP.DYN.LE00.IN/years")
        assert years.json() == [2021, 2020]

        observations = client.get(
            "/health/data/indicators/SP.DYN.LE00.IN/observations?year=2020"
        )
        body = observations.json()
        assert observations.status_code == 200
        assert body["year"] == 2020
        assert body["observations"][0]["country_iso3"] == "PHL"
        assert body["observations"][0]["value"] == 71.2
        assert body["observations"][0]["unit"] == "years"
        assert body["observations"][0]["source"] == "World Bank — World Development Indicators"
    finally:
        engine.dispose()


def test_country_profile_and_history_are_year_filtered():
    client, engine = make_client()
    try:
        country = client.get(
            "/health/data/countries/phl/observations?year=2020"
        )
        assert country.status_code == 200
        assert country.json()["country"]["iso3"] == "PHL"
        assert [row["year"] for row in country.json()["observations"]] == [2020]

        history = client.get(
            "/health/data/countries/PHL/indicators/SP.DYN.LE00.IN/history"
        )
        assert history.status_code == 200
        assert [row["year"] for row in history.json()] == [2020, 2021]
    finally:
        engine.dispose()


def test_missing_indicator_or_country_returns_not_found():
    client, engine = make_client()
    try:
        assert client.get("/health/data/indicators/unknown/years").status_code == 404
        assert client.get("/health/data/countries/ZZZ/observations").status_code == 404
    finally:
        engine.dispose()


def test_who_provenance_and_country_year_coverage_are_exposed():
    client, engine = make_client()
    try:
        with Session(engine) as db:
            db.add(
                HealthDataSource(
                    code="who-gho-odata",
                    name="World Health Organization Global Health Observatory",
                    url="https://ghoapi.azureedge.net/api",
                )
            )
            db.add(
                HealthIndicator(
                    code="WHOSIS_000003",
                    name="Neonatal mortality rate",
                    definition="Deaths in the first 28 days per 1,000 live births.",
                    unit="deaths per 1,000 live births",
                    source_code="who-gho-odata",
                    publisher="WHO and UN IGME",
                    definition_url="https://www.who.int/data/gho/indicator-metadata-registry",
                    dataset_code="WHOSIS_000003",
                    dataset_name="WHO neonatal mortality estimates",
                )
            )
            db.flush()
            db.add(
                HealthIndicatorObservation(
                    country_iso3="PHL",
                    indicator_code="WHOSIS_000003",
                    year=2020,
                    value=12.4,
                    unit="deaths per 1,000 live births",
                    source_code="who-gho-odata",
                    source_reference="https://ghoapi.azureedge.net/api/WHOSIS_000003",
                    source_record_timestamp=datetime(2025, 1, 1),
                    source_value_text="12.4 [11.0-13.5]",
                    dimensions_json=json.dumps(
                        {"Dim1": "SEX_BTSX", "Dim2": "AGEGROUP_DAYS0-27"}
                    ),
                    uncertainty_lower=11.0,
                    uncertainty_upper=13.5,
                    estimate_status="modeled_estimate",
                )
            )
            db.commit()

        response = client.get(
            "/health/data/indicators/WHOSIS_000003/observations?year=2020"
        )
        assert response.status_code == 200
        body = response.json()
        assert body["indicator"]["publisher"] == "WHO and UN IGME"
        assert body["indicator"]["dataset_code"] == "WHOSIS_000003"
        observation = body["observations"][0]
        assert observation["source"] == "World Health Organization Global Health Observatory"
        assert observation["source_record_timestamp"].startswith("2025-01-01")
        assert observation["source_publication_date"] is None
        assert observation["dimensions"] == {
            "Dim1": "SEX_BTSX",
            "Dim2": "AGEGROUP_DAYS0-27",
        }
        assert observation["uncertainty_lower"] == 11.0
        assert observation["uncertainty_upper"] == 13.5

        coverage = client.get(
            "/health/data/coverage?indicator_code=WHOSIS_000003&country_iso3=phl"
        )
        assert coverage.status_code == 200
        assert coverage.json()[0]["observed_years"] == [2020]
        assert coverage.json()[0]["unobserved_years_within_span"] == []
        assert "cadence is indicator-" in coverage.json()[0]["cadence_note"]
        assert client.get("/health/data/coverage?country_iso3=12!").status_code == 422
    finally:
        engine.dispose()
