import json

import pytest
import requests
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.models.health_indicator import (
    HealthCountry,
    HealthDataImport,
    HealthIndicatorObservation,
    HealthIndicatorObservationRevision,
)
from app.services.who_gho_service import (
    WHO_GHO_API_URL,
    WHO_INDICATORS,
    WhoGhoClient,
    ingest_who_gho,
    parse_gho_observation,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    session.add_all(
        [
            HealthCountry(
                iso3="PHL",
                iso2="PH",
                name="Philippines",
                region="Western Pacific",
            ),
            HealthCountry(
                iso3="SGP",
                iso2="SG",
                name="Singapore",
                region="Western Pacific",
            ),
        ]
    )
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def neonatal_row(country="PHL", year=2020, value=12.4, record_date="2025-01-01T00:00:00Z"):
    return {
        "SpatialDim": country,
        "SpatialDimType": "COUNTRY",
        "TimeDim": year,
        "NumericValue": value,
        "Low": 11.0,
        "High": 13.5,
        "Dim1": "SEX_BTSX",
        "Dim1Type": "SEX",
        "Dim2": "AGEGROUP_DAYS0-27",
        "Dim2Type": "AGEGROUP",
        "Date": record_date,
        "Value": "12.4 [11.0-13.5]",
        "Comments": None,
    }


class FakeWhoGhoClient:
    def __init__(self, rows):
        self.rows = rows

    def fetch_indicator(self, code):
        return {
            "IndicatorCode": code,
            "IndicatorName": WHO_INDICATORS[code].name,
            "Language": "EN",
        }

    def fetch_observations(self, code, start_year, end_year):
        return [
            row
            for row in self.rows
            if start_year <= int(row["TimeDim"]) <= end_year
        ]

    def fetch_country_metadata(self, country_codes):
        country_names = {
            "COK": ("Cook Islands", "Western Pacific"),
            "NIU": ("Niue", "Western Pacific"),
        }
        return [
            {
                "CountryCode": code,
                "CountryName": country_names[code][0],
                "RegionName": country_names[code][1],
                "Language": "EN",
            }
            for code in country_codes
            if code in country_names
        ]


def test_gho_parser_preserves_uncertainty_and_neonatal_dimensions():
    parsed = parse_gho_observation("WHOSIS_000003", neonatal_row(), 2000, 2025)

    assert parsed is not None
    key, observation = parsed
    assert key == ("PHL", 2020)
    assert observation["unit"] == "deaths per 1,000 live births"
    assert observation["uncertainty_lower"] == 11.0
    assert observation["uncertainty_upper"] == 13.5
    assert json.loads(observation["dimensions_json"]) == {
        "Dim1": "SEX_BTSX",
        "Dim1Type": "SEX",
        "Dim2": "AGEGROUP_DAYS0-27",
        "Dim2Type": "AGEGROUP",
    }
    assert observation["source_publication_date"] is None
    assert observation["source_record_timestamp"].isoformat() == "2025-01-01T00:00:00"


def test_gho_parser_keeps_nulls_missing_and_rejects_bad_rows():
    assert (
        parse_gho_observation(
            "WHOSIS_000003",
            neonatal_row(value=None),
            2000,
            2025,
        )
        is None
    )

    invalid_rows = [
        {**neonatal_row(), "SpatialDim": "WB_HI", "SpatialDimType": "WORLDBANKINCOMEGROUP"},
        {**neonatal_row(), "TimeDim": 2026},
        {**neonatal_row(), "Dim1": "SEX_MLE"},
        {**neonatal_row(), "Low": 13.0, "High": 12.0},
        {**neonatal_row(), "Unit": "percent"},
    ]
    for row in invalid_rows:
        with pytest.raises(ValueError):
            parse_gho_observation("WHOSIS_000003", row, 2000, 2025)


def test_who_client_follows_official_pagination_and_keeps_dimension_filter(monkeypatch):
    client = WhoGhoClient()
    requests_seen = []

    class JsonResponse:
        status_code = 200

        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    next_link = f"{WHO_GHO_API_URL}/WHOSIS_000003?$skip=1"

    def fake_get(url, params=None, **kwargs):
        requests_seen.append((url, params))
        if len(requests_seen) == 1:
            return JsonResponse(
                {"value": [neonatal_row()], "@odata.nextLink": next_link}
            )
        return JsonResponse({"value": [neonatal_row(country="SGP")]})

    monkeypatch.setattr(client.session, "get", fake_get)
    rows = client.fetch_observations("WHOSIS_000003", 2000, 2025)

    assert len(rows) == 2
    filter_text = requests_seen[0][1]["$filter"]
    assert "SpatialDimType eq 'COUNTRY'" in filter_text
    assert "Dim1 eq 'SEX_BTSX'" in filter_text
    assert "Dim2 eq 'AGEGROUP_DAYS0-27'" in filter_text
    assert requests_seen[1][0] == next_link
    assert requests_seen[1][1] is None


def test_who_client_uses_skip_pagination_when_provider_omits_next_link(monkeypatch):
    client = WhoGhoClient(page_size=2)
    requests_seen = []

    class JsonResponse:
        status_code = 200

        def __init__(self, rows):
            self.rows = rows

        def raise_for_status(self):
            return None

        def json(self):
            return {"value": self.rows}

    pages = [
        [neonatal_row(), neonatal_row(country="SGP", year=2021)],
        [neonatal_row(country="COK", year=2022)],
    ]

    def fake_get(url, params=None, **kwargs):
        requests_seen.append((url, params))
        return JsonResponse(pages[len(requests_seen) - 1])

    monkeypatch.setattr(client.session, "get", fake_get)
    rows = client.fetch_observations("WHOSIS_000003", 2000, 2025)

    assert len(rows) == 3
    assert requests_seen[1][1]["$skip"] == 2


def test_who_client_rejects_pagination_outside_official_origin(monkeypatch):
    client = WhoGhoClient()

    class JsonResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"value": [], "@odata.nextLink": "https://example.test/api/next"}

    monkeypatch.setattr(client.session, "get", lambda *args, **kwargs: JsonResponse())
    with pytest.raises(ValueError, match="left the official API origin"):
        client.fetch_observations("WHOSIS_000003", 2000, 2025)


def test_who_import_is_idempotent_and_audits_changed_values(db):
    client = FakeWhoGhoClient(
        [
            neonatal_row(),
            neonatal_row(country="SGP", value=1.2),
        ]
    )
    first = ingest_who_gho(db, 2000, 2025, ["WHOSIS_000003"], client)[0]
    second = ingest_who_gho(db, 2000, 2025, ["WHOSIS_000003"], client)[0]

    assert (first.rows_inserted, first.rows_updated) == (2, 0)
    assert (second.rows_inserted, second.rows_updated) == (0, 2)
    assert second.rows_duplicate == 0
    assert db.scalar(select(func.count()).select_from(HealthIndicatorObservation)) == 2
    assert (
        db.scalar(select(func.count()).select_from(HealthIndicatorObservationRevision))
        == 0
    )

    client.rows = [
        neonatal_row(value=13.0, record_date="2026-01-01T00:00:00Z")
    ]
    revised = ingest_who_gho(db, 2000, 2025, ["WHOSIS_000003"], client)[0]
    assert revised.rows_updated == 1
    history = db.scalars(select(HealthIndicatorObservationRevision)).all()
    assert len(history) == 1
    assert history[0].previous_value == 12.4
    stored = db.scalar(
        select(HealthIndicatorObservation).where(
            HealthIndicatorObservation.country_iso3 == "PHL"
        )
    )
    assert stored.value == 13.0
    assert stored.source_record_timestamp.year == 2026


def test_who_import_adds_official_country_metadata_for_missing_iso3(db):
    result = ingest_who_gho(
        db,
        2000,
        2025,
        ["WHOSIS_000003"],
        FakeWhoGhoClient([neonatal_row(country="COK")]),
    )[0]
    country = db.get(HealthCountry, "COK")

    assert result.rows_inserted == 1
    assert country is not None
    assert country.name == "Cook Islands"
    assert country.region == "Western Pacific"


def test_who_import_selects_latest_duplicate_and_rejects_ambiguous_revision(db):
    rows = [
        neonatal_row(value=12.4, record_date="2025-01-01T00:00:00Z"),
        neonatal_row(value=13.0, record_date="2026-01-01T00:00:00Z"),
    ]
    result = ingest_who_gho(
        db,
        2000,
        2025,
        ["WHOSIS_000003"],
        FakeWhoGhoClient(rows),
    )[0]
    assert result.rows_duplicate == 1
    assert result.rows_inserted == 1
    stored = db.scalar(select(HealthIndicatorObservation))
    assert stored.value == 13.0

    conflicting = [
        neonatal_row(value=10.0, record_date="2026-01-01T00:00:00Z"),
        neonatal_row(value=11.0, record_date="2026-01-01T00:00:00Z"),
    ]
    with pytest.raises(ValueError, match="Conflicting duplicate WHO rows"):
        ingest_who_gho(
            db,
            2000,
            2025,
            ["WHOSIS_000003"],
            FakeWhoGhoClient(conflicting),
        )
    failed_runs = db.scalars(
        select(HealthDataImport).where(HealthDataImport.status == "failed")
    ).all()
    assert len(failed_runs) == 1


def test_who_import_failure_is_recorded(db):
    class FailingClient(FakeWhoGhoClient):
        def fetch_indicator(self, code):
            raise requests.Timeout("WHO GHO timed out")

    with pytest.raises(requests.Timeout):
        ingest_who_gho(
            db,
            2000,
            2025,
            ["WHOSIS_000003"],
            FailingClient([]),
        )
    run = db.scalar(select(HealthDataImport))
    assert run.status == "failed"
    assert run.source_code == "who-gho-odata"
    assert "timed out" in run.error_message
