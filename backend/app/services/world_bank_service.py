import csv
import io
import logging
import math
import re
import time
import zipfile
from pathlib import Path
from typing import Any, Iterator, TextIO

import requests
from requests.adapters import HTTPAdapter
from sqlalchemy import delete, func, select, text, tuple_
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session
from urllib3.util.retry import Retry
from urllib3.exceptions import ReadTimeoutError

from app.models.health_indicator import (
    HealthCountry,
    HealthDataImport,
    HealthDataImportCheckpoint,
    HealthDataSource,
    HealthIndicator,
    HealthIndicatorObservation,
)
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

WORLD_BANK_SOURCE_CODE = "world-bank-wdi"
WORLD_BANK_SOURCE_NAME = "World Bank — World Development Indicators"
WORLD_BANK_BASE_URL = "https://api.worldbank.org/v2"
PAGE_SIZE = 500
COUNTRY_PAGE_SIZE = 50

INDICATOR_UNITS = {
    "SP.DYN.LE00.IN": "years",
    "SP.POP.TOTL": "people",
    "SH.DYN.MORT": "deaths per 1,000 live births",
    "SH.XPD.CHEX.GD.ZS": "% of GDP",
}

INDICATOR_METADATA = {
    "SP.DYN.LE00.IN": (
        "Life expectancy at birth, total (years)",
        "Life expectancy at birth indicates the number of years a newborn infant would live if prevailing patterns of mortality at the time of its birth were to stay the same throughout its life.",
    ),
    "SP.POP.TOTL": (
        "Population, total",
        "Total population is based on the de facto definition of population, which counts all residents regardless of legal status or citizenship. The values shown are midyear estimates.",
    ),
    "SH.DYN.MORT": (
        "Mortality rate, under-5 (per 1,000 live births)",
        "Under-five mortality rate is the probability per 1,000 that a newborn baby will die before reaching age five, if subject to age-specific mortality rates of the specified year.",
    ),
    "SH.XPD.CHEX.GD.ZS": (
        "Current health expenditure (% of GDP)",
        "Level of current health expenditure expressed as a percentage of GDP. Estimates of current health expenditures include healthcare goods and services consumed during each year. This indicator does not include capital health expenditures such as buildings, machinery, IT and stocks of vaccines for emergency or outbreaks.",
    ),
}


def normalize_iso3(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    code = value.strip().upper()
    return code if re.fullmatch(r"[A-Z]{3}", code) else None


def parse_observation(row: dict[str, Any]) -> tuple[str, int, float] | None:
    """Validate a World Bank row; null indicator values remain absent."""
    country = row.get("countryiso3code")
    iso3 = normalize_iso3(country)
    if iso3 is None:
        raise ValueError(f"Invalid ISO-3 country code: {country!r}")

    year_value = row.get("date")
    if not isinstance(year_value, str) or not re.fullmatch(r"\d{4}", year_value):
        raise ValueError(f"Invalid reporting year: {year_value!r}")
    year = int(year_value)
    if year < 1900 or year > utc_now().year:
        raise ValueError(f"Reporting year is out of range: {year}")

    value = row.get("value")
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError(f"Invalid numeric observation: {value!r}")
    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid numeric observation: {value!r}") from exc
    if not math.isfinite(numeric_value) or numeric_value < 0:
        raise ValueError(f"Observation must be finite and non-negative: {value!r}")
    return iso3, year, numeric_value


def _is_read_timeout(exception: BaseException) -> bool:
    pending = [exception]
    visited: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in visited:
            continue
        visited.add(id(current))
        if isinstance(current, (requests.Timeout, ReadTimeoutError)):
            return True
        pending.extend(
            candidate
            for candidate in (
                current.__cause__,
                current.__context__,
                getattr(current, "reason", None),
                *current.args,
            )
            if isinstance(candidate, BaseException)
        )
    return False


class WorldBankClient:
    def __init__(
        self,
        timeout: tuple[float, float] = (10, 90),
        session: requests.Session | None = None,
        retries: int = 2,
        per_page: int = PAGE_SIZE,
    ) -> None:
        if retries < 0:
            raise ValueError("Retry count cannot be negative")
        if per_page < 1:
            raise ValueError("Page size must be positive")
        self.timeout = timeout
        self.per_page = per_page
        self.session = session or requests.Session()
        retry = Retry(
            total=retries,
            connect=retries,
            read=retries,
            status=retries,
            backoff_factor=1,
            backoff_jitter=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _get_json(self, url: str, params: dict[str, Any]) -> Any:
        started = time.perf_counter()
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "HealthScope-AI/2.0",
                },
            )
            logger.info(
                "World Bank API response: status=%d elapsed=%.2fs url=%s params=%s",
                getattr(response, "status_code", "unknown"),
                time.perf_counter() - started,
                url,
                params,
            )
            response.raise_for_status()
        except requests.Timeout:
            logger.warning(
                "World Bank API network timeout: elapsed=%.2fs url=%s connect_timeout=%s read_timeout=%s",
                time.perf_counter() - started,
                url,
                self.timeout[0],
                self.timeout[1],
            )
            raise
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else "unknown"
            logger.error(
                "World Bank API returned HTTP %s for url=%s",
                status_code,
                url,
            )
            raise
        except requests.RequestException as exc:
            if _is_read_timeout(exc):
                logger.warning(
                    "World Bank API read timeout after retries: elapsed=%.2fs url=%s read_timeout=%s",
                    time.perf_counter() - started,
                    url,
                    self.timeout[1],
                )
            else:
                logger.exception("World Bank API network request failed: url=%s", url)
            raise
        try:
            return response.json()
        except ValueError as exc:
            logger.error("World Bank API returned invalid JSON: url=%s", url)
            raise ValueError(f"World Bank returned invalid JSON for {url}") from exc

    def _get_all_pages(
        self,
        url: str,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        page = 1
        results: list[dict[str, Any]] = []
        while True:
            payload = self._get_json(url, {**params, "page": page})
            if (
                not isinstance(payload, list)
                or len(payload) != 2
                or not isinstance(payload[0], dict)
            ):
                raise ValueError("Unexpected World Bank API response format")
            page_info, rows = payload
            if rows is None and page_info.get("total") == 0:
                return results
            if not isinstance(rows, list):
                raise ValueError("World Bank API response did not contain a row list")
            if not all(isinstance(row, dict) for row in rows):
                raise ValueError("World Bank API response contained an invalid row")
            results.extend(rows)
            page_count = page_info.get("pages")
            if not isinstance(page_count, int) or page_count < 1:
                raise ValueError("World Bank API response contained invalid pagination")
            if page >= page_count:
                return results
            page += 1

    def fetch_countries(self, country_iso3: str | None = None) -> list[dict[str, Any]]:
        country = normalize_iso3(country_iso3) if country_iso3 is not None else None
        if country_iso3 is not None and country is None:
            raise ValueError(f"Invalid ISO-3 country code: {country_iso3!r}")
        return self._get_all_pages(
            f"{WORLD_BANK_BASE_URL}/country/{country or 'all'}",
            {"format": "json", "per_page": COUNTRY_PAGE_SIZE},
        )

    def fetch_indicator(self, code: str) -> dict[str, Any]:
        payload = self._get_json(
            f"{WORLD_BANK_BASE_URL}/indicator/{code}",
            {"format": "json"},
        )
        if (
            not isinstance(payload, list)
            or len(payload) != 2
            or not isinstance(payload[1], list)
            or not payload[1]
            or not isinstance(payload[1][0], dict)
        ):
            raise ValueError(f"World Bank indicator metadata is missing for {code}")
        return payload[1][0]

    def fetch_observations(
        self,
        code: str,
        start_year: int,
        end_year: int,
        country_iso3: str | None = None,
    ) -> list[dict[str, Any]]:
        country = normalize_iso3(country_iso3) if country_iso3 is not None else None
        if country_iso3 is not None and country is None:
            raise ValueError(f"Invalid ISO-3 country code: {country_iso3!r}")
        return self._get_all_pages(
            f"{WORLD_BANK_BASE_URL}/country/{country or 'all'}/indicator/{code}",
            {
                "format": "json",
                "per_page": COUNTRY_PAGE_SIZE if country else self.per_page,
                "date": f"{start_year}:{end_year}",
            },
        )

    def fetch_observation_page(
        self,
        code: str,
        start_year: int,
        end_year: int,
        page: int,
        country_iso3: str | None = None,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        country = normalize_iso3(country_iso3) if country_iso3 is not None else None
        if country_iso3 is not None and country is None:
            raise ValueError(f"Invalid ISO-3 country code: {country_iso3!r}")
        payload = self._get_json(
            f"{WORLD_BANK_BASE_URL}/country/{country or 'all'}/indicator/{code}",
            {
                "format": "json",
                "per_page": COUNTRY_PAGE_SIZE if country else self.per_page,
                "date": f"{start_year}:{end_year}",
                "page": page,
            },
        )
        if (
            not isinstance(payload, list)
            or len(payload) != 2
            or not isinstance(payload[0], dict)
        ):
            raise ValueError("Unexpected World Bank API response format")
        page_info, rows = payload
        if rows is None and page_info.get("total") == 0:
            rows = []
        if (
            not isinstance(rows, list)
            or not all(isinstance(row, dict) for row in rows)
            or not isinstance(page_info.get("pages"), int)
            or page_info["pages"] < 1
            or not isinstance(page_info.get("total"), int)
        ):
            raise ValueError("World Bank API response contained invalid pagination or rows")
        logger.info(
            "World Bank observation page: indicator=%s years=%d-%d page=%d/%d total=%d rows=%d",
            code,
            start_year,
            end_year,
            page,
            page_info["pages"],
            page_info["total"],
            len(rows),
        )
        return page_info, rows


def ensure_source(db: Session) -> None:
    db.execute(
        sqlite_insert(HealthDataSource)
        .values(
            code=WORLD_BANK_SOURCE_CODE,
            name=WORLD_BANK_SOURCE_NAME,
            url=WORLD_BANK_BASE_URL,
            updated_at=utc_now(),
        )
        .on_conflict_do_update(
            index_elements=[HealthDataSource.code],
            set_={
                "name": WORLD_BANK_SOURCE_NAME,
                "url": WORLD_BANK_BASE_URL,
                "updated_at": utc_now(),
            },
        )
    )
    db.commit()


def ensure_checkpoint_schema(db: Session) -> None:
    columns = {
        row[1]
        for row in db.execute(text("PRAGMA table_info(health_data_import_checkpoints)"))
    }
    if columns and "page_size" not in columns:
        db.execute(
            text(
                "ALTER TABLE health_data_import_checkpoints "
                "ADD COLUMN page_size INTEGER NOT NULL DEFAULT 500"
            )
        )
        db.commit()


def _upsert_countries(
    db: Session,
    countries: dict[str, dict[str, Any]],
) -> int:
    if not countries:
        return 0
    statement = sqlite_insert(HealthCountry).values(list(countries.values()))
    db.execute(
        statement.on_conflict_do_update(
            index_elements=[HealthCountry.iso3],
            set_={
                "iso2": func.coalesce(statement.excluded.iso2, HealthCountry.iso2),
                "name": statement.excluded.name,
                "region": func.coalesce(statement.excluded.region, HealthCountry.region),
                "income_level": func.coalesce(
                    statement.excluded.income_level,
                    HealthCountry.income_level,
                ),
                "updated_at": statement.excluded.updated_at,
            },
        )
    )
    db.commit()
    return len(countries)


def ingest_countries(
    db: Session,
    client: WorldBankClient,
    country_iso3: str | None = None,
) -> int:
    rows = client.fetch_countries(country_iso3)
    countries: dict[str, dict[str, Any]] = {}
    for row in rows:
        region = row.get("region")
        if not isinstance(region, dict) or region.get("value") == "Aggregates":
            continue
        iso3 = normalize_iso3(row.get("id"))
        name = row.get("name")
        if iso3 is None or not isinstance(name, str) or not name.strip():
            continue
        iso2 = row.get("iso2Code")
        countries[iso3] = {
            "iso3": iso3,
            "iso2": iso2.strip().upper() if isinstance(iso2, str) and len(iso2.strip()) == 2 else None,
            "name": name.strip(),
            "region": region.get("value") or None,
            "income_level": (row.get("incomeLevel") or {}).get("value"),
            "updated_at": utc_now(),
        }

    count = _upsert_countries(db, countries)
    logger.info("Synchronized %d World Bank country records", count)
    return count


def _upsert_indicator_metadata(
    db: Session,
    code: str,
    name: str,
    definition: str,
) -> None:
    statement = sqlite_insert(HealthIndicator).values(
        code=code,
        name=name.strip(),
        definition=definition.strip(),
        unit=INDICATOR_UNITS[code],
        source_code=WORLD_BANK_SOURCE_CODE,
        updated_at=utc_now(),
    )
    db.execute(
        statement.on_conflict_do_update(
            index_elements=[HealthIndicator.code],
            set_={
                "name": statement.excluded.name,
                "definition": statement.excluded.definition,
                "unit": statement.excluded.unit,
                "source_code": statement.excluded.source_code,
                "updated_at": statement.excluded.updated_at,
            },
        )
    )


def _upsert_observation_batch(
    db: Session,
    code: str,
    observations: dict[tuple[str, int], dict[str, Any]],
    run: HealthDataImport,
) -> None:
    if not observations:
        return
    keys = list(observations)
    existing = _existing_observation_keys(db, code, keys)
    run.rows_updated += len(existing)
    run.rows_inserted += len(keys) - len(existing)
    excluded = sqlite_insert(HealthIndicatorObservation).excluded
    db.execute(
        sqlite_insert(HealthIndicatorObservation)
        .values(list(observations.values()))
        .on_conflict_do_update(
            index_elements=[
                HealthIndicatorObservation.country_iso3,
                HealthIndicatorObservation.indicator_code,
                HealthIndicatorObservation.year,
            ],
            set_={
                "value": excluded.value,
                "unit": excluded.unit,
                "source_code": excluded.source_code,
                "imported_at": excluded.imported_at,
            },
        )
    )


def _existing_observation_keys(
    db: Session,
    code: str,
    keys: list[tuple[str, int]],
) -> set[tuple[str, int]]:
    existing: set[tuple[str, int]] = set()
    for offset in range(0, len(keys), 400):
        batch = keys[offset : offset + 400]
        rows = db.execute(
            select(
                HealthIndicatorObservation.country_iso3,
                HealthIndicatorObservation.year,
            ).where(
                HealthIndicatorObservation.indicator_code == code,
                tuple_(
                    HealthIndicatorObservation.country_iso3,
                    HealthIndicatorObservation.year,
                ).in_(batch),
            )
        )
        existing.update((country, year) for country, year in rows)
    return existing


def ingest_indicator(
    db: Session,
    client: WorldBankClient,
    code: str,
    start_year: int,
    end_year: int,
    country_iso3: str | None = None,
    batch_years: int = 5,
    per_page: int = PAGE_SIZE,
    resume: bool = False,
) -> HealthDataImport:
    if code not in INDICATOR_UNITS:
        raise ValueError(f"Unsupported World Bank indicator: {code}")
    if start_year < 1900 or end_year < start_year or end_year > utc_now().year:
        raise ValueError("Invalid World Bank import year range")
    if batch_years < 1:
        raise ValueError("Year batch size must be positive")
    if per_page < 1:
        raise ValueError("Page size must be positive")
    country = normalize_iso3(country_iso3) if country_iso3 is not None else None
    if country_iso3 is not None and country is None:
        raise ValueError(f"Invalid ISO-3 country code: {country_iso3!r}")
    country_key = country or ""
    page_size = COUNTRY_PAGE_SIZE if country else per_page

    ensure_checkpoint_schema(db)
    ensure_source(db)
    run = HealthDataImport(
        source_code=WORLD_BANK_SOURCE_CODE,
        status="running",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        metadata = client.fetch_indicator(code)
        if metadata.get("id") != code or not isinstance(metadata.get("name"), str):
            raise ValueError(f"World Bank metadata did not match indicator {code}")
        definition = metadata.get("sourceNote")
        if not isinstance(definition, str) or not definition.strip():
            raise ValueError(f"World Bank definition is missing for indicator {code}")

        _upsert_indicator_metadata(db, code, metadata["name"], definition)
        run.indicator_code = code
        db.commit()

        for batch_start in range(start_year, end_year + 1, batch_years):
            batch_end = min(batch_start + batch_years - 1, end_year)
            page_number = 1
            page_info: dict[str, Any] | None = None
            page_rows: list[dict[str, Any]] = []
            if hasattr(client, "fetch_observation_page"):
                page_info, page_rows = client.fetch_observation_page(
                    code,
                    batch_start,
                    batch_end,
                    page_number,
                    country_iso3=country,
                )
            else:
                page_rows = client.fetch_observations(
                    code,
                    batch_start,
                    batch_end,
                    country_iso3=country,
                )
                page_info = {
                    "page": 1,
                    "pages": 1,
                    "total": len(page_rows),
                    "per_page": page_size,
                }

            page_count = page_info.get("pages")
            if not isinstance(page_count, int) or page_count < 1:
                raise ValueError("World Bank API response contained invalid pagination")

            if page_number == 1 and resume:
                previous = db.scalars(
                    select(HealthDataImportCheckpoint).where(
                        HealthDataImportCheckpoint.indicator_code == code,
                        HealthDataImportCheckpoint.country_key == country_key,
                        HealthDataImportCheckpoint.start_year == batch_start,
                        HealthDataImportCheckpoint.end_year == batch_end,
                        HealthDataImportCheckpoint.page_size == page_size,
                    )
                ).all()
                if previous and any(item.pages_total != page_count for item in previous):
                    db.execute(
                        delete(HealthDataImportCheckpoint).where(
                            HealthDataImportCheckpoint.indicator_code == code,
                            HealthDataImportCheckpoint.country_key == country_key,
                            HealthDataImportCheckpoint.start_year == batch_start,
                            HealthDataImportCheckpoint.end_year == batch_end,
                            HealthDataImportCheckpoint.page_size == page_size,
                        )
                    )
                    db.commit()
                    previous = []

            for page_number in range(1, page_count + 1):
                checkpoint = db.scalar(
                    select(HealthDataImportCheckpoint).where(
                        HealthDataImportCheckpoint.indicator_code == code,
                        HealthDataImportCheckpoint.country_key == country_key,
                        HealthDataImportCheckpoint.start_year == batch_start,
                        HealthDataImportCheckpoint.end_year == batch_end,
                        HealthDataImportCheckpoint.page_size == page_size,
                        HealthDataImportCheckpoint.page == page_number,
                    )
                )
                if resume and checkpoint is not None:
                    logger.info(
                        "Resuming World Bank import: skipping completed page %d/%d for %s %d-%d",
                        page_number,
                        page_count,
                        code,
                        batch_start,
                        batch_end,
                    )
                    continue

                if page_number > 1:
                    if not hasattr(client, "fetch_observation_page"):
                        raise ValueError(
                            "Client pagination metadata requires fetch_observation_page"
                        )
                    page_info, page_rows = client.fetch_observation_page(
                        code,
                        batch_start,
                        batch_end,
                        page_number,
                        country_iso3=country,
                    )
                    if page_info.get("pages") != page_count:
                        raise ValueError("World Bank pagination changed during batch import")

                run.rows_received += len(page_rows)
                country_codes = {
                    normalize_iso3(row.get("countryiso3code")) for row in page_rows
                }
                known_countries = set(
                    db.scalars(
                        select(HealthCountry.iso3).where(
                            HealthCountry.iso3.in_(
                                [country_code for country_code in country_codes if country_code]
                            )
                        )
                    )
                )
                observations: dict[tuple[str, int], dict[str, Any]] = {}
                for row in page_rows:
                    value = row.get("value")
                    if value is None or value == "":
                        run.rows_missing += 1
                        continue
                    try:
                        parsed = parse_observation(row)
                        if parsed is None:
                            run.rows_missing += 1
                            continue
                        iso3, year, numeric_value = parsed
                        if not batch_start <= year <= batch_end:
                            raise ValueError(
                                f"Reporting year {year} is outside batch {batch_start}-{batch_end}"
                            )
                        if iso3 not in known_countries:
                            raise ValueError(
                                f"Country code {iso3} is not in World Bank metadata"
                            )
                    except ValueError as exc:
                        run.rows_rejected += 1
                        logger.warning("Skipping invalid World Bank row for %s: %s", code, exc)
                        continue
                    observations[(iso3, year)] = {
                        "country_iso3": iso3,
                        "indicator_code": code,
                        "year": year,
                        "value": numeric_value,
                        "unit": INDICATOR_UNITS[code],
                        "source_code": WORLD_BANK_SOURCE_CODE,
                        "imported_at": utc_now(),
                    }

                _upsert_observation_batch(db, code, observations, run)
                db.execute(
                    sqlite_insert(HealthDataImportCheckpoint)
                    .values(
                        indicator_code=code,
                        country_key=country_key,
                        start_year=batch_start,
                        end_year=batch_end,
                        page_size=page_size,
                        page=page_number,
                        pages_total=page_count,
                        completed_at=utc_now(),
                    )
                    .on_conflict_do_update(
                        index_elements=[
                            HealthDataImportCheckpoint.indicator_code,
                            HealthDataImportCheckpoint.country_key,
                            HealthDataImportCheckpoint.start_year,
                            HealthDataImportCheckpoint.end_year,
                            HealthDataImportCheckpoint.page,
                        ],
                        set_={
                            "pages_total": page_count,
                            "completed_at": utc_now(),
                        },
                    )
                )
                db.commit()
                logger.info(
                    "Completed World Bank page %d/%d for %s, years %d-%d (%d response rows)",
                    page_number,
                    page_count,
                    code,
                    batch_start,
                    batch_end,
                    len(page_rows),
                )

        run.status = "success"
        run.completed_at = utc_now()
        run.error_message = None
        db.commit()
        logger.info(
            "Imported World Bank indicator %s: %d inserted, %d updated, %d missing, %d rejected",
            code,
            run.rows_inserted,
            run.rows_updated,
            run.rows_missing,
            run.rows_rejected,
        )
        return run
    except Exception as exc:
        db.rollback()
        failed_run = db.get(HealthDataImport, run.id)
        if failed_run is not None:
            failed_run.status = "failed"
            failed_run.completed_at = utc_now()
            failed_run.error_message = str(exc)[:2000]
            db.commit()
        logger.exception("World Bank import failed for %s", code)
        raise


def ingest_world_bank(
    db: Session,
    start_year: int,
    end_year: int,
    indicator_codes: list[str] | None = None,
    client: WorldBankClient | None = None,
    country_iso3: str | None = None,
    batch_years: int = 5,
    per_page: int = PAGE_SIZE,
    resume: bool = False,
    timeout: tuple[float, float] = (10, 90),
    retries: int = 2,
) -> list[HealthDataImport]:
    bank_client = client or WorldBankClient(
        timeout=timeout,
        retries=retries,
        per_page=per_page,
    )
    country = normalize_iso3(country_iso3) if country_iso3 is not None else None
    if country_iso3 is not None and country is None:
        raise ValueError(f"Invalid ISO-3 country code: {country_iso3!r}")
    ensure_source(db)
    ingest_countries(db, bank_client, country)
    codes = indicator_codes or list(INDICATOR_UNITS)
    imports: list[HealthDataImport] = []
    failures: list[tuple[str, Exception]] = []
    for code in codes:
        try:
            imports.append(
                ingest_indicator(
                    db,
                    bank_client,
                    code,
                    start_year,
                    end_year,
                    country_iso3=country,
                    batch_years=batch_years,
                    per_page=per_page,
                    resume=resume,
                )
            )
        except Exception as exc:
            failures.append((code, exc))
    if failures:
        failed_codes = ", ".join(code for code, _ in failures)
        raise RuntimeError(f"World Bank imports failed for: {failed_codes}") from failures[0][1]
    return imports


def _csv_dict_rows(
    stream: TextIO,
    required_fields: set[str],
) -> tuple[list[str], Iterator[dict[str, str | None]]]:
    reader = csv.reader(stream)
    required = {field.casefold() for field in required_fields}
    for row in reader:
        header = []
        for cell in row:
            field = cell.strip().lstrip("\ufeff")
            year_match = re.fullmatch(r"(\d{4})\s+\[YR\1\]", field, re.IGNORECASE)
            if year_match:
                field = year_match.group(1)
            elif field.casefold() == "series code":
                field = "Indicator Code"
            header.append(field)
        if required.issubset({field.casefold() for field in header}):
            def rows() -> Iterator[dict[str, str | None]]:
                for values in reader:
                    yield {
                        field: values[index] if index < len(values) else None
                        for index, field in enumerate(header)
                    }

            return header, rows()
    raise ValueError(
        f"CSV header is missing required fields: {', '.join(sorted(required_fields))}"
    )


def _iter_csv_rows(
    stream: TextIO,
    required_fields: set[str],
    required_years: set[str] | None = None,
) -> Iterator[dict[str, str | None]]:
    header, rows = _csv_dict_rows(stream, required_fields)
    year_columns = {
        field for field in header
        if re.fullmatch(r"\d{4}", field)
    }
    missing_years = (required_years or set()).difference(year_columns)
    if required_years is not None and missing_years:
        missing = ", ".join(sorted(missing_years))
        raise ValueError(f"World Bank CSV is missing requested years: {missing}")
    yield from rows


def _csv_members(path: Path) -> tuple[bool, list[str], list[str]]:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        country_files = [
            name for name in members
            if "metadata_country" in Path(name).name.casefold()
        ]
        data_files = [
            name for name in members
            if "metadata" not in Path(name).name.casefold()
        ]
        if not data_files:
            raise ValueError("World Bank ZIP archive contains no data CSV file")
        return True, country_files, data_files
    if path.suffix.casefold() == ".csv":
        return False, [], [path.name]
    raise ValueError("Input must be a World Bank .csv file or .zip archive")


def _open_csv_rows(
    path: Path,
    member: str,
    required_fields: set[str],
    required_years: set[str] | None = None,
) -> Iterator[dict[str, str | None]]:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            with archive.open(member) as binary:
                with io.TextIOWrapper(binary, encoding="utf-8-sig", newline="") as text:
                    yield from _iter_csv_rows(text, required_fields, required_years)
        return
    with path.open("r", encoding="utf-8-sig", newline="") as text:
        yield from _iter_csv_rows(text, required_fields, required_years)


def _upsert_csv_country_metadata(
    db: Session,
    path: Path,
    country_files: list[str],
    country_iso3: str | None,
) -> int:
    countries: dict[str, dict[str, Any]] = {}
    for member in country_files:
        for row in _open_csv_rows(
            path,
            member,
            {"Country Code", "Region"},
        ):
            iso3 = normalize_iso3(row.get("Country Code"))
            region = (row.get("Region") or "").strip()
            name = (
                row.get("Table Name")
                or row.get("Country Name")
                or row.get("Country")
                or ""
            ).strip()
            if (
                iso3 is None
                or not name
                or not region
                or region.casefold() == "aggregates"
                or (country_iso3 is not None and iso3 != country_iso3)
            ):
                continue
            income_level = (
                row.get("Income Group")
                or row.get("Income Level")
                or ""
            ).strip()
            countries[iso3] = {
                "iso3": iso3,
                "iso2": None,
                "name": name,
                "region": region,
                "income_level": income_level or None,
                "updated_at": utc_now(),
            }
    return _upsert_countries(db, countries)


def _iter_indicator_csv_observations(
    path: Path,
    data_files: list[str],
    code: str,
    start_year: int,
    end_year: int,
    country_iso3: str | None,
) -> Iterator[dict[str, Any]]:
    for member in data_files:
        for row in _open_csv_rows(
            path,
            member,
            {"Country Code", "Indicator Code"},
            {str(year) for year in range(start_year, end_year + 1)},
        ):
            if (row.get("Indicator Code") or "").strip() != code:
                continue
            iso3_value = row.get("Country Code")
            iso3 = normalize_iso3(iso3_value)
            if country_iso3 is not None and iso3 != country_iso3:
                continue
            for year in range(start_year, end_year + 1):
                yield {
                    "countryiso3code": iso3_value,
                    "date": str(year),
                    "value": row.get(str(year)),
                }


def ingest_world_bank_csv(
    db: Session,
    archive_path: str | Path,
    start_year: int,
    end_year: int,
    indicator_codes: list[str] | None = None,
    country_iso3: str | None = None,
) -> list[HealthDataImport]:
    path = Path(archive_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"World Bank CSV archive not found: {path}")
    if start_year < 1900 or end_year < start_year or end_year > utc_now().year:
        raise ValueError("Invalid World Bank import year range")

    country = normalize_iso3(country_iso3) if country_iso3 is not None else None
    if country_iso3 is not None and country is None:
        raise ValueError(f"Invalid ISO-3 country code: {country_iso3!r}")
    codes = indicator_codes or list(INDICATOR_UNITS)
    unsupported = set(codes).difference(INDICATOR_UNITS)
    if unsupported:
        raise ValueError(f"Unsupported World Bank indicators: {', '.join(sorted(unsupported))}")

    is_zip, country_files, data_files = _csv_members(path)
    if is_zip:
        country_count = _upsert_csv_country_metadata(
            db,
            path,
            country_files,
            country,
        )
        if country_count:
            logger.info("Loaded %d country records from World Bank CSV metadata", country_count)
    ensure_source(db)

    imports: list[HealthDataImport] = []
    failures: list[tuple[str, Exception]] = []
    for code in codes:
        run = HealthDataImport(
            source_code=WORLD_BANK_SOURCE_CODE,
            status="running",
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        try:
            name, definition = INDICATOR_METADATA[code]
            _upsert_indicator_metadata(db, code, name, definition)
            run.indicator_code = code
            db.commit()

            known_countries = set(db.scalars(select(HealthCountry.iso3)))
            pending: dict[tuple[str, int], dict[str, Any]] = {}
            for row in _iter_indicator_csv_observations(
                path,
                data_files,
                code,
                start_year,
                end_year,
                country,
            ):
                run.rows_received += 1
                if row["value"] in ("", ".."):
                    row["value"] = None
                try:
                    parsed = parse_observation(row)
                    if parsed is None:
                        run.rows_missing += 1
                        continue
                    iso3, year, value = parsed
                    if iso3 not in known_countries:
                        run.rows_rejected += 1
                        continue
                except ValueError as exc:
                    run.rows_rejected += 1
                    logger.warning(
                        "Skipping invalid World Bank CSV row for %s: %s",
                        code,
                        exc,
                    )
                    continue

                pending[(iso3, year)] = {
                    "country_iso3": iso3,
                    "indicator_code": code,
                    "year": year,
                    "value": value,
                    "unit": INDICATOR_UNITS[code],
                    "source_code": WORLD_BANK_SOURCE_CODE,
                    "imported_at": utc_now(),
                }
                if len(pending) >= 500:
                    _upsert_observation_batch(db, code, pending, run)
                    pending = {}
            if pending:
                _upsert_observation_batch(db, code, pending, run)
            if run.rows_received == 0:
                raise ValueError(f"No {code} rows found in the selected CSV year range")

            run.status = "success"
            run.completed_at = utc_now()
            run.error_message = None
            db.commit()
            imports.append(run)
            logger.info(
                "Imported CSV indicator %s: %d inserted, %d updated, %d missing, %d rejected",
                code,
                run.rows_inserted,
                run.rows_updated,
                run.rows_missing,
                run.rows_rejected,
            )
        except Exception as exc:
            db.rollback()
            failed_run = db.get(HealthDataImport, run.id)
            if failed_run is not None:
                failed_run.status = "failed"
                failed_run.completed_at = utc_now()
                failed_run.error_message = str(exc)[:2000]
                db.commit()
            logger.exception("World Bank CSV import failed for %s", code)
            failures.append((code, exc))

    if failures:
        failed_codes = ", ".join(code for code, _ in failures)
        raise RuntimeError(f"World Bank CSV imports failed for: {failed_codes}") from failures[0][1]
    return imports
