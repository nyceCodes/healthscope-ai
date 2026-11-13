from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
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
        db.add_all(
            [
                HealthCountry(
                    iso3="PHL",
                    iso2="PH",
                    name="Philippines",
                    region="East Asia & Pacific",
                ),
                HealthCountry(
                    iso3="SGP",
                    iso2="SG",
                    name="Singapore",
                    region="East Asia & Pacific",
                ),
                HealthCountry(
                    iso3="USA",
                    iso2="US",
                    name="United States",
                    region="North America",
                ),
            ]
        )
        db.add(
            HealthDataSource(
                code="world-bank-wdi",
                name="World Bank — World Development Indicators",
                url="https://api.worldbank.org/v2",
            )
        )
        db.flush()
        db.add_all(
            [
                HealthIndicator(
                    code="SP.DYN.LE00.IN",
                    name="Life expectancy at birth",
                    definition="Life expectancy under current mortality patterns.",
                    unit="years",
                    source_code="world-bank-wdi",
                ),
                HealthIndicator(
                    code="SH.XPD.CHEX.GD.ZS",
                    name="Current health expenditure",
                    definition="Health expenditure as share of GDP.",
                    unit="% of GDP",
                    source_code="world-bank-wdi",
                ),
            ]
        )
        db.flush()
        db.add_all(
            [
                HealthIndicatorObservation(
                    country_iso3="PHL",
                    indicator_code="SP.DYN.LE00.IN",
                    year=2020,
                    value=70,
                    unit="years",
                    source_code="world-bank-wdi",
                ),
                HealthIndicatorObservation(
                    country_iso3="PHL",
                    indicator_code="SP.DYN.LE00.IN",
                    year=2022,
                    value=72,
                    unit="years",
                    source_code="world-bank-wdi",
                ),
                HealthIndicatorObservation(
                    country_iso3="SGP",
                    indicator_code="SP.DYN.LE00.IN",
                    year=2020,
                    value=80,
                    unit="years",
                    source_code="world-bank-wdi",
                ),
                HealthIndicatorObservation(
                    country_iso3="SGP",
                    indicator_code="SP.DYN.LE00.IN",
                    year=2021,
                    value=81,
                    unit="years",
                    source_code="world-bank-wdi",
                ),
                HealthIndicatorObservation(
                    country_iso3="SGP",
                    indicator_code="SP.DYN.LE00.IN",
                    year=2022,
                    value=82,
                    unit="years",
                    source_code="world-bank-wdi",
                ),
                HealthIndicatorObservation(
                    country_iso3="PHL",
                    indicator_code="SH.XPD.CHEX.GD.ZS",
                    year=2022,
                    value=4.5,
                    unit="% of GDP",
                    source_code="world-bank-wdi",
                ),
                HealthIndicatorObservation(
                    country_iso3="SGP",
                    indicator_code="SH.XPD.CHEX.GD.ZS",
                    year=2022,
                    value=5.5,
                    unit="% of GDP",
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


def test_singapore_profile_returns_stored_values_with_year_and_source():
    client, engine = make_client()
    try:
        response = client.get("/health/data/countries/sgp/observations")
        assert response.status_code == 200
        body = response.json()
        assert body["country"]["iso3"] == "SGP"
        assert body["country"]["region"] == "East Asia & Pacific"
        life = next(
            row for row in body["observations"]
            if row["indicator_code"] == "SP.DYN.LE00.IN"
        )
        assert (life["value"], life["year"], life["unit"]) == (82, 2022, "years")
        assert life["source"] == "World Bank — World Development Indicators"
    finally:
        engine.dispose()


def test_trends_filter_years_and_calculate_change_from_actual_observations():
    client, engine = make_client()
    try:
        response = client.get(
            "/health/data/analytics/trends",
            params=[
                ("indicator_code", "SP.DYN.LE00.IN"),
                ("countries", "PHL"),
                ("countries", "SGP"),
                ("start_year", "2021"),
                ("end_year", "2022"),
            ],
        )
        assert response.status_code == 200
        body = response.json()
        philippines, singapore = body["series"]
        assert [row["year"] for row in philippines["observations"]] == [2022]
        assert philippines["absolute_change"] is None
        assert [row["year"] for row in singapore["observations"]] == [2021, 2022]
        assert singapore["absolute_change"] == 1
        assert round(singapore["percent_change"], 4) == 1.2346
        assert singapore["change_from_year"] == 2021
        assert singapore["change_to_year"] == 2022
    finally:
        engine.dispose()


def test_comparison_includes_missing_countries_and_valid_differences():
    client, engine = make_client()
    try:
        response = client.get(
            "/health/data/analytics/compare",
            params=[
                ("indicator_code", "SP.DYN.LE00.IN"),
                ("year", "2022"),
                ("countries", "PHL"),
                ("countries", "SGP"),
                ("countries", "USA"),
            ],
        )
        assert response.status_code == 200
        rows = response.json()["countries"]
        assert rows[0]["observation"]["year"] == 2022
        assert rows[0]["difference_from_reference"] == 0
        assert rows[1]["difference_from_reference"] == 10
        assert round(rows[1]["percent_difference_from_reference"], 4) == 13.8889
        assert rows[2]["observation"] is None
        assert rows[2]["difference_from_reference"] is None
    finally:
        engine.dispose()


def test_rankings_sort_values_and_exclude_missing_observations():
    client, engine = make_client()
    try:
        ascending = client.get(
            "/health/data/analytics/rankings",
            params={
                "indicator_code": "SP.DYN.LE00.IN",
                "year": 2022,
                "order": "ascending",
            },
        )
        descending = client.get(
            "/health/data/analytics/rankings",
            params={
                "indicator_code": "SP.DYN.LE00.IN",
                "year": 2022,
                "order": "descending",
            },
        )
        assert [row["observation"]["country_iso3"] for row in ascending.json()["rows"]] == [
            "PHL",
            "SGP",
        ]
        assert [row["rank"] for row in descending.json()["rows"]] == [1, 2]
        assert descending.json()["rows"][0]["observation"]["country_iso3"] == "SGP"
    finally:
        engine.dispose()


def test_relative_changes_are_unavailable_for_zero_baselines():
    client, engine = make_client()
    try:
        session_factory = sessionmaker(bind=engine)
        with session_factory() as db:
            db.add(
                HealthIndicatorObservation(
                    country_iso3="PHL",
                    indicator_code="SP.DYN.LE00.IN",
                    year=2021,
                    value=0,
                    unit="years",
                    source_code="world-bank-wdi",
                )
            )
            db.commit()

        trends = client.get(
            "/health/data/analytics/trends",
            params=[
                ("indicator_code", "SP.DYN.LE00.IN"),
                ("countries", "PHL"),
                ("start_year", "2021"),
                ("end_year", "2022"),
            ],
        )
        comparison = client.get(
            "/health/data/analytics/compare",
            params=[
                ("indicator_code", "SP.DYN.LE00.IN"),
                ("year", "2021"),
                ("countries", "PHL"),
                ("countries", "SGP"),
            ],
        )
        assert trends.json()["series"][0]["absolute_change"] == 72
        assert trends.json()["series"][0]["percent_change"] is None
        assert comparison.json()["countries"][1]["difference_from_reference"] == 81
        assert comparison.json()["countries"][1]["percent_difference_from_reference"] is None
    finally:
        engine.dispose()


def test_invalid_trend_period_and_comparison_country_count_are_rejected():
    client, engine = make_client()
    try:
        invalid_period = client.get(
            "/health/data/analytics/trends",
            params={
                "indicator_code": "SP.DYN.LE00.IN",
                "countries": "PHL",
                "start_year": 2022,
                "end_year": 2020,
            },
        )
        invalid_comparison = client.get(
            "/health/data/analytics/compare",
            params={
                "indicator_code": "SP.DYN.LE00.IN",
                "year": 2022,
                "countries": "PHL",
            },
        )
        assert invalid_period.status_code == 422
        assert invalid_comparison.status_code == 422
    finally:
        engine.dispose()
