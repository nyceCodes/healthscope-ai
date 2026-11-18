import logging
import zipfile

import pytest
import requests
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from urllib3.exceptions import MaxRetryError, ReadTimeoutError

from app.database.database import Base
from app.models.health_indicator import (
    HealthCountry,
    HealthDataImport,
    HealthDataImportCheckpoint,
    HealthIndicatorObservation,
    HealthIndicatorObservationRevision,
)
from app.services.world_bank_service import (
    WorldBankClient,
    ingest_countries,
    ingest_indicator,
    ingest_world_bank_csv,
    normalize_iso3,
    parse_observation,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


class FakeWorldBankClient:
    def __init__(self, rows=None):
        self.rows = rows or []

    def fetch_indicator(self, code):
        return {
            "id": code,
            "name": "Life expectancy at birth, total (years)",
            "sourceNote": "Official World Bank definition.",
        }

    def fetch_observations(self, code, start_year, end_year, country_iso3=None):
        return self.rows

    def fetch_countries(self, country_iso3=None):
        return [
            {
                "id": "phl",
                "iso2Code": "ph",
                "name": "Philippines",
                "region": {"value": "East Asia & Pacific"},
                "incomeLevel": {"value": "Lower middle income"},
            },
            {
                "id": "WLD",
                "name": "World",
                "region": {"value": "Aggregates"},
                "incomeLevel": {"value": "Aggregates"},
            },
        ]


def valid_rows():
    return [
        {"countryiso3code": "phl", "date": "2020", "value": "71.2"},
        {"countryiso3code": "PHL", "date": "2021", "value": None},
        {"countryiso3code": "PHL", "date": "2022", "value": 72.1},
    ]


def test_iso3_normalization_and_missing_observations():
    assert normalize_iso3(" phl ") == "PHL"
    assert normalize_iso3("PH") is None
    assert parse_observation(
        {"countryiso3code": "phl", "date": "2020", "value": "71.2"}
    ) == ("PHL", 2020, 71.2)
    assert parse_observation(
        {"countryiso3code": "PHL", "date": "2020", "value": None}
    ) is None
    with pytest.raises(ValueError):
        parse_observation(
            {"countryiso3code": "PHL", "date": "2020", "value": "NaN"}
        )


def test_country_ingestion_normalizes_iso_and_skips_aggregates(db):
    imported = ingest_countries(db, FakeWorldBankClient())

    assert imported == 1
    country = db.get(HealthCountry, "PHL")
    assert country is not None
    assert country.iso2 == "PH"
    assert country.region == "East Asia & Pacific"
    assert db.get(HealthCountry, "WLD") is None


def test_indicator_ingestion_is_repeatable_and_keeps_nulls_missing(db):
    ingest_countries(db, FakeWorldBankClient())
    client = FakeWorldBankClient(valid_rows())

    first = ingest_indicator(db, client, "SP.DYN.LE00.IN", 2020, 2022)
    second = ingest_indicator(db, client, "SP.DYN.LE00.IN", 2020, 2022)

    assert (first.rows_inserted, first.rows_updated, first.rows_missing) == (2, 0, 1)
    assert (second.rows_inserted, second.rows_updated, second.rows_missing) == (0, 2, 1)
    assert db.scalar(select(func.count()).select_from(HealthIndicatorObservation)) == 2
    assert db.scalar(
        select(HealthIndicatorObservation.value).where(
            HealthIndicatorObservation.year == 2020
        )
    ) == 71.2
    assert db.scalar(
        select(HealthIndicatorObservation.year).where(
            HealthIndicatorObservation.year == 2021
        )
    ) is None
    assert db.scalar(
        select(func.count()).select_from(HealthIndicatorObservationRevision)
    ) == 0


def test_indicator_reimport_updates_changed_values(db):
    ingest_countries(db, FakeWorldBankClient())
    client = FakeWorldBankClient(valid_rows())
    ingest_indicator(db, client, "SP.DYN.LE00.IN", 2020, 2022)
    client.rows = [
        {"countryiso3code": "PHL", "date": "2020", "value": 73.0},
    ]

    result = ingest_indicator(db, client, "SP.DYN.LE00.IN", 2020, 2020)

    assert result.rows_updated == 1
    assert result.rows_inserted == 0
    assert db.scalar(select(HealthIndicatorObservation.value)) == 73.0
    assert db.scalar(select(func.count()).select_from(HealthIndicatorObservation)) == 2
    revision = db.scalar(select(HealthIndicatorObservationRevision))
    assert revision.previous_value == 71.2


def test_world_bank_request_failures_are_reported_and_recorded(db, caplog):
    class FailingClient(FakeWorldBankClient):
        def fetch_observations(
            self,
            code,
            start_year,
            end_year,
            country_iso3=None,
        ):
            raise requests.Timeout("World Bank timed out")

    with caplog.at_level(logging.ERROR):
        with pytest.raises(requests.Timeout):
            ingest_indicator(
                db,
                FailingClient(),
                "SP.DYN.LE00.IN",
                2020,
                2024,
            )

    run = db.scalar(select(HealthDataImport))
    assert run is not None
    assert run.status == "failed"
    assert run.indicator_code == "SP.DYN.LE00.IN"
    assert "timed out" in run.error_message
    assert "World Bank import failed" in caplog.text


def test_indicator_metadata_failure_is_recorded(db):
    class FailingMetadataClient(FakeWorldBankClient):
        def fetch_indicator(self, code):
            raise requests.Timeout("World Bank metadata timed out")

    with pytest.raises(requests.Timeout):
        ingest_indicator(
            db,
            FailingMetadataClient(),
            "SP.DYN.LE00.IN",
            2020,
            2024,
        )

    run = db.scalar(select(HealthDataImport))
    assert run is not None
    assert run.status == "failed"
    assert run.indicator_code is None
    assert "metadata timed out" in run.error_message


def test_world_bank_client_propagates_http_errors(monkeypatch):
    def fail_request(*args, **kwargs):
        raise requests.Timeout("timeout")

    client = WorldBankClient()
    monkeypatch.setattr(client.session, "get", fail_request)

    with pytest.raises(requests.Timeout):
        client.fetch_indicator("SP.DYN.LE00.IN")


def test_world_bank_client_logs_exhausted_read_timeout_separately(caplog, monkeypatch):
    client = WorldBankClient()
    timeout = ReadTimeoutError(None, "/v2/indicator", "read timed out")
    exhausted_retries = requests.ConnectionError(
        MaxRetryError(None, "/v2/indicator", timeout)
    )

    def fail_request(*args, **kwargs):
        raise exhausted_retries

    monkeypatch.setattr(client.session, "get", fail_request)

    with caplog.at_level(logging.WARNING):
        with pytest.raises(requests.ConnectionError):
            client.fetch_indicator("SP.DYN.LE00.IN")

    assert "read timeout after retries" in caplog.text


def test_world_bank_client_reads_paginated_observation_responses(monkeypatch):
    rows = [
        {"countryiso3code": "PHL", "date": "2020", "value": 71.2},
        {"countryiso3code": "PHL", "date": "2021", "value": 71.5},
    ]
    payloads = [
        [{"page": 1, "pages": 2, "total": 2}, rows[:1]],
        [{"page": 2, "pages": 2, "total": 2}, rows[1:]],
    ]
    requested_params = []
    requested_urls = []

    class JsonResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    client = WorldBankClient()

    def fake_get(url, params, **kwargs):
        requested_urls.append(url)
        requested_params.append(params)
        return JsonResponse(payloads[params["page"] - 1])

    monkeypatch.setattr(client.session, "get", fake_get)
    result = client.fetch_observations(
        "SP.DYN.LE00.IN",
        2020,
        2021,
        country_iso3="PHL",
    )

    assert result == rows
    assert [params["page"] for params in requested_params] == [1, 2]
    assert requested_params[0]["date"] == "2020:2021"
    assert requested_params[0]["per_page"] == 50
    assert "country/PHL/indicator/" in requested_urls[0]


def test_batched_import_checkpoints_pages_and_resumes(db):
    ingest_countries(db, FakeWorldBankClient())

    class PagedClient(FakeWorldBankClient):
        def __init__(self):
            super().__init__()
            self.page_requests = []

        def fetch_observation_page(
            self,
            code,
            start_year,
            end_year,
            page,
            country_iso3=None,
        ):
            self.page_requests.append((start_year, end_year, page))
            year = start_year if page == 1 else end_year
            row = {
                "countryiso3code": "PHL",
                "date": str(year),
                "value": str(70 + year - 2000),
            }
            return {"page": page, "pages": 2, "total": 2}, [row]

    client = PagedClient()
    first = ingest_indicator(
        db,
        client,
        "SP.DYN.LE00.IN",
        2000,
        2009,
        batch_years=5,
        per_page=500,
    )
    assert first.rows_inserted == 4
    assert client.page_requests == [
        (2000, 2004, 1),
        (2000, 2004, 2),
        (2005, 2009, 1),
        (2005, 2009, 2),
    ]
    assert db.scalar(select(func.count()).select_from(HealthDataImportCheckpoint)) == 4

    client.page_requests.clear()
    resumed = ingest_indicator(
        db,
        client,
        "SP.DYN.LE00.IN",
        2000,
        2009,
        batch_years=5,
        per_page=500,
        resume=True,
    )
    assert resumed.rows_inserted == 0
    assert resumed.rows_updated == 0
    assert client.page_requests == [(2000, 2004, 1), (2005, 2009, 1)]
    assert db.scalar(select(func.count()).select_from(HealthIndicatorObservation)) == 4


def test_world_bank_client_fetches_single_observation_page(monkeypatch):
    client = WorldBankClient(per_page=500)
    requested = []

    class JsonResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return [
                {"page": 2, "pages": 3, "per_page": 500, "total": 1100},
                [{"countryiso3code": "PHL", "date": "2022", "value": 20}],
            ]

    def fake_get(url, params, **kwargs):
        requested.append((url, params))
        return JsonResponse()

    monkeypatch.setattr(client.session, "get", fake_get)
    page_info, rows = client.fetch_observation_page(
        "SH.DYN.MORT",
        2020,
        2024,
        2,
    )

    assert page_info["pages"] == 3
    assert rows[0]["value"] == 20
    assert requested[0][1]["per_page"] == 500
    assert requested[0][1]["page"] == 2
    assert requested[0][1]["date"] == "2020:2024"


def test_official_csv_zip_import_is_validated_and_idempotent(db, tmp_path):
    db.add(
        HealthCountry(
            iso3="PHL",
            iso2="PH",
            name="Philippines",
            region="East Asia & Pacific",
        )
    )
    db.commit()
    archive_path = tmp_path / "WDI.zip"
    data_csv = (
        "World Development Indicators\n"
        "Downloaded from https://api.worldbank.org/\n"
        "Country Name,Country Code,Indicator Name,Indicator Code,2022,2023,2024\n"
        "Philippines,PHL,Population total,SP.POP.TOTL,113964338,,115843670\n"
        "Singapore,SGP,Population total,SP.POP.TOTL,5637022,5917648,\n"
        "World,WLD,Population total,SP.POP.TOTL,8000000000,8100000000,8200000000\n"
    )
    country_csv = (
        "Country Code,Region,Income Group,Table Name\n"
        "PHL,East Asia & Pacific,Lower middle income,Philippines\n"
        "SGP,East Asia & Pacific,High income,Singapore\n"
        "WLD,Aggregates,Aggregates,World\n"
    )
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("API_SP.POP.TOTL_DS2_en_csv_v2/Data.csv", data_csv)
        archive.writestr("Metadata_Country.csv", country_csv)

    first = ingest_world_bank_csv(
        db,
        archive_path,
        2022,
        2024,
        indicator_codes=["SP.POP.TOTL"],
    )[0]
    second = ingest_world_bank_csv(
        db,
        archive_path,
        2022,
        2024,
        indicator_codes=["SP.POP.TOTL"],
    )[0]

    assert first.rows_received == 9
    assert first.rows_missing == 2
    assert first.rows_rejected == 3
    assert (first.rows_inserted, first.rows_updated) == (4, 0)
    assert (second.rows_inserted, second.rows_updated) == (0, 4)
    assert db.scalar(select(func.count()).select_from(HealthIndicatorObservation)) == 4
    assert db.get(HealthCountry, "WLD") is None
    philippines = db.get(HealthCountry, "PHL")
    assert philippines is not None
    assert philippines.iso2 == "PH"

    philippines_2022 = db.scalar(
        select(HealthIndicatorObservation).where(
            HealthIndicatorObservation.country_iso3 == "PHL",
            HealthIndicatorObservation.year == 2022,
        )
    )
    assert philippines_2022 is not None
    assert philippines_2022.value == 113964338
    assert philippines_2022.unit == "people"
    assert philippines_2022.source_code == "world-bank-wdi"


def test_databank_export_headers_import_multiple_indicators(db, tmp_path):
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
        ]
    )
    db.commit()
    archive_path = tmp_path / "DataBank.zip"
    data_csv = (
        "Country Name,Country Code,Series Name,Series Code,"
        "2024 [YR2024],2023 [YR2023],2022 [YR2022]\n"
        "Philippines,PHL,Mortality,SH.DYN.MORT,26.5,27,27.5\n"
        "Singapore,SGP,Mortality,SH.DYN.MORT,2.4,2.5,2.6\n"
        "Philippines,PHL,Health expenditure,SH.XPD.CHEX.GD.ZS,5.2,5.1,..\n"
        "Singapore,SGP,Health expenditure,SH.XPD.CHEX.GD.ZS,4.7,4.6,4.5\n"
    )
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("P_Data.csv", data_csv)
        archive.writestr(
            "P_Series - Metadata.csv",
            "Series Code,Series Name\nSH.DYN.MORT,Mortality\n",
        )

    imports = ingest_world_bank_csv(
        db,
        archive_path,
        2022,
        2024,
        indicator_codes=["SH.DYN.MORT", "SH.XPD.CHEX.GD.ZS"],
    )
    by_code = {run.indicator_code: run for run in imports}

    assert by_code["SH.DYN.MORT"].rows_received == 6
    assert by_code["SH.DYN.MORT"].rows_inserted == 6
    assert by_code["SH.XPD.CHEX.GD.ZS"].rows_received == 6
    assert by_code["SH.XPD.CHEX.GD.ZS"].rows_inserted == 5
    assert by_code["SH.XPD.CHEX.GD.ZS"].rows_missing == 1
    assert db.scalar(
        select(HealthIndicatorObservation.value).where(
            HealthIndicatorObservation.country_iso3 == "PHL",
            HealthIndicatorObservation.indicator_code == "SH.XPD.CHEX.GD.ZS",
            HealthIndicatorObservation.year == 2022,
        )
    ) is None
    assert db.scalar(
        select(HealthIndicatorObservation.value).where(
            HealthIndicatorObservation.country_iso3 == "PHL",
            HealthIndicatorObservation.indicator_code == "SH.DYN.MORT",
            HealthIndicatorObservation.year == 2024,
        )
    ) == 26.5
    assert db.scalar(select(func.count()).select_from(HealthIndicatorObservation)) == 11

    repeated = ingest_world_bank_csv(
        db,
        archive_path,
        2022,
        2024,
        indicator_codes=["SH.DYN.MORT", "SH.XPD.CHEX.GD.ZS"],
    )
    assert all(run.rows_inserted == 0 for run in repeated)
    assert sum(run.rows_updated for run in repeated) == 11
    assert db.scalar(select(func.count()).select_from(HealthIndicatorObservation)) == 11


def test_csv_import_records_invalid_headers_without_importing_values(db, tmp_path):
    archive_path = tmp_path / "invalid.csv"
    archive_path.write_text(
        "Country Name,Country Code,2022\nPhilippines,PHL,113964338\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="SP.POP.TOTL"):
        ingest_world_bank_csv(
            db,
            archive_path,
            2022,
            2022,
            indicator_codes=["SP.POP.TOTL"],
        )

    run = db.scalar(select(HealthDataImport))
    assert run is not None
    assert run.status == "failed"
    assert "required fields" in run.error_message
    assert db.scalar(select(func.count()).select_from(HealthIndicatorObservation)) == 0
