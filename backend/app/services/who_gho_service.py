import json
import logging
import math
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session
from urllib3.util.retry import Retry

from app.database.database import ensure_health_data_schema
from app.models.health_indicator import (
    HealthCountry,
    HealthDataImport,
    HealthDataSource,
    HealthIndicator,
)
from app.services.observation_service import upsert_observation_batch
from app.utils.country_codes import normalize_iso3
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

WHO_GHO_API_URL = "https://ghoapi.azureedge.net/api"
WHO_GHO_SOURCE_CODE = "who-gho-odata"
WHO_GHO_SOURCE_NAME = "World Health Organization Global Health Observatory"
WHO_INDICATOR_REGISTRY_URL = (
    "https://www.who.int/data/gho/indicator-metadata-registry"
)


@dataclass(frozen=True)
class WhoIndicatorSpec:
    name: str
    definition: str
    unit: str
    publisher: str
    dataset_name: str
    estimate_status: str
    denominator_definition: str
    dimensions: tuple[tuple[str, str], ...] = ()


WHO_INDICATORS = {
    "MDG_0000000026": WhoIndicatorSpec(
        name="Maternal mortality ratio (per 100 000 live births)",
        definition=(
            "Maternal deaths per 100,000 live births. WHO series values are "
            "estimates; the reporting year is the observation year."
        ),
        unit="deaths per 100,000 live births",
        publisher="WHO and the UN Maternal Mortality Estimation Inter-Agency Group",
        dataset_name="WHO maternal mortality estimates",
        estimate_status="modeled_estimate",
        denominator_definition="Live births in the same reporting period",
    ),
    "WHOSIS_000003": WhoIndicatorSpec(
        name="Neonatal mortality rate (per 1000 live births)",
        definition=(
            "Deaths during the first 28 completed days of life per 1,000 live "
            "births. The imported series is restricted to both sexes and ages "
            "0-27 days; it is an estimate."
        ),
        unit="deaths per 1,000 live births",
        publisher="WHO and the UN Inter-agency Group for Child Mortality Estimation",
        dataset_name="WHO/UNICEF/UN IGME neonatal mortality estimates",
        estimate_status="modeled_estimate",
        denominator_definition="Live births in the same reporting period",
        dimensions=(
            ("Dim1", "SEX_BTSX"),
            ("Dim2", "AGEGROUP_DAYS0-27"),
        ),
    ),
    "WHS4_100": WhoIndicatorSpec(
        name=(
            "Diphtheria tetanus toxoid and pertussis third-dose (DTP3) "
            "immunization coverage among 1-year-olds (%) (WUENIC)"
        ),
        definition=(
            "WHO/UNICEF Estimates of National Immunization Coverage for the "
            "third dose of DTP-containing vaccine among children aged one year."
        ),
        unit="percent",
        publisher="World Health Organization and UNICEF",
        dataset_name="WHO/UNICEF Estimates of National Immunization Coverage (WUENIC)",
        estimate_status="WHO_UNICEF_estimate",
        denominator_definition="Children aged one year in the reporting population",
    ),
    "MDG_0000000020": WhoIndicatorSpec(
        name="Incidence of tuberculosis (per 100 000 population per year)",
        definition=(
            "Estimated new and relapse tuberculosis cases per 100,000 population "
            "per year. This is an incidence estimate, not prevalence or mortality."
        ),
        unit="cases per 100,000 population per year",
        publisher="World Health Organization",
        dataset_name="WHO Global Tuberculosis Programme estimates",
        estimate_status="modeled_estimate",
        denominator_definition="Mid-year population in the reporting year",
    ),
    "MDG_0000000025": WhoIndicatorSpec(
        name="Births attended by skilled health personnel (%)",
        definition=(
            "Percentage of births attended by skilled health personnel. Source "
            "and collection method can vary by country and reporting year."
        ),
        unit="percent of births",
        publisher="World Health Organization and UNICEF",
        dataset_name="WHO/UNICEF skilled birth attendance data",
        estimate_status="source_method_varies_by_country_year",
        denominator_definition="Total births in the reporting population",
    ),
    "UHC_INDEX_REPORTED": WhoIndicatorSpec(
        name="UHC Service Coverage Index (SDG 3.8.1)",
        definition=(
            "UHC service coverage index on a 0-100 scale. It is a composite "
            "index, not a percent of people covered or an individual measure."
        ),
        unit="index (0-100)",
        publisher="World Health Organization",
        dataset_name="WHO UHC service coverage monitoring",
        estimate_status="composite_index",
        denominator_definition="Not applicable: composite index without a single denominator",
    ),
}


def _numeric_value(value: Any, label: str, allow_none: bool = False) -> float | None:
    if value is None or value == "":
        if allow_none:
            return None
        raise ValueError(f"{label} is missing")
    if isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(numeric) or numeric < 0:
        raise ValueError(f"{label} must be finite and non-negative")
    return numeric


def _parse_timestamp(value: Any, label: str, allow_none: bool = True) -> datetime | None:
    if value is None or value == "":
        if allow_none:
            return None
        raise ValueError(f"{label} is missing")
    if not isinstance(value, str):
        raise ValueError(f"{label} must be an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO timestamp") from exc
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def parse_gho_observation(
    code: str,
    row: dict[str, Any],
    start_year: int,
    end_year: int,
) -> tuple[tuple[str, int], dict[str, Any]] | None:
    spec = WHO_INDICATORS.get(code)
    if spec is None:
        raise ValueError(f"Unsupported WHO GHO indicator: {code}")
    if row.get("IndicatorCode") not in (None, code):
        raise ValueError(f"WHO row indicator code did not match {code}")

    country_type = row.get("SpatialDimType")
    iso3 = normalize_iso3(row.get("SpatialDim"))
    if country_type != "COUNTRY" or iso3 is None:
        raise ValueError("WHO row does not contain a valid country ISO-3 code")

    year_value = row.get("TimeDim")
    if isinstance(year_value, bool) or not re.fullmatch(r"\d{4}", str(year_value or "")):
        raise ValueError(f"Invalid WHO reporting year: {year_value!r}")
    year = int(year_value)
    if year < 1900 or year > utc_now().year:
        raise ValueError(f"WHO reporting year is out of range: {year}")
    if not start_year <= year <= end_year:
        raise ValueError(f"WHO reporting year {year} is outside the requested range")

    actual_dimensions = {
        key: str(row.get(key)).strip()
        for key in ("Dim1", "Dim2", "Dim3")
        if row.get(key) not in (None, "")
    }
    expected_dimensions = dict(spec.dimensions)
    if actual_dimensions != expected_dimensions:
        raise ValueError(
            f"WHO dimensions did not match the approved series for {code}"
        )

    row_unit = row.get("Unit") or row.get("UnitName")
    if row_unit is not None and str(row_unit).strip().casefold() != spec.unit.casefold():
        raise ValueError(f"WHO unit did not match the approved unit for {code}")

    numeric = _numeric_value(
        row.get("NumericValue"),
        "WHO NumericValue",
        allow_none=True,
    )
    if numeric is None:
        return None

    lower = _numeric_value(row.get("Low"), "WHO lower uncertainty bound", True)
    upper = _numeric_value(row.get("High"), "WHO upper uncertainty bound", True)
    if (lower is None) != (upper is None):
        raise ValueError("WHO uncertainty bounds must both be present or both absent")
    if lower is not None and upper is not None and lower > upper:
        raise ValueError("WHO uncertainty lower bound exceeds its upper bound")

    denominator_value = _numeric_value(
        row.get("DenominatorValue"),
        "WHO denominator value",
        allow_none=True,
    )
    publication_date = _parse_timestamp(
        row.get("PublicationDate"),
        "WHO publication date",
    )
    record_timestamp = _parse_timestamp(row.get("Date"), "WHO source record timestamp")
    comments = row.get("Comments")
    if comments is not None and not isinstance(comments, str):
        raise ValueError("WHO source comments must be text")

    dimension_details: dict[str, str] = {}
    for key in (
        "Dim1Type",
        "Dim1",
        "Dim2Type",
        "Dim2",
        "Dim3Type",
        "Dim3",
    ):
        value = row.get(key)
        if value not in (None, ""):
            dimension_details[key] = str(value).strip()

    observation = {
        "country_iso3": iso3,
        "indicator_code": code,
        "year": year,
        "value": numeric,
        "unit": spec.unit,
        "source_code": WHO_GHO_SOURCE_CODE,
        "imported_at": utc_now(),
        "source_reference": comments.strip() if comments and comments.strip() else (
            f"{WHO_GHO_API_URL}/{code}"
        ),
        "source_publication_date": publication_date,
        "source_record_timestamp": record_timestamp,
        "source_value_text": (
            str(row["Value"]) if row.get("Value") is not None else None
        ),
        "denominator_value": denominator_value,
        "denominator_definition": spec.denominator_definition,
        "dimensions_json": json.dumps(
            dimension_details,
            sort_keys=True,
            separators=(",", ":"),
        ),
        "uncertainty_lower": lower,
        "uncertainty_upper": upper,
        "estimate_status": spec.estimate_status,
    }
    return (iso3, year), observation


class WhoGhoClient:
    def __init__(
        self,
        timeout: tuple[float, float] = (10, 60),
        session: requests.Session | None = None,
        page_size: int = 1000,
    ) -> None:
        if page_size < 1 or page_size > 1000:
            raise ValueError("WHO GHO page size must be between 1 and 1000")
        self.timeout = timeout
        self.page_size = page_size
        self.session = session or requests.Session()
        retry = Retry(
            total=2,
            connect=2,
            read=2,
            status=2,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)

    def _get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
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
                "WHO GHO API response: status=%d elapsed=%.2fs url=%s",
                response.status_code,
                time.perf_counter() - started,
                url,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            logger.exception("WHO GHO API request failed: url=%s", url)
            raise
        except ValueError as exc:
            logger.error("WHO GHO API returned invalid JSON: url=%s", url)
            raise ValueError(f"WHO GHO returned invalid JSON for {url}") from exc

    def fetch_indicator(self, code: str) -> dict[str, Any]:
        if code not in WHO_INDICATORS:
            raise ValueError(f"Unsupported WHO GHO indicator: {code}")
        payload = self._get_json(
            f"{WHO_GHO_API_URL}/Indicator",
            {"$filter": f"IndicatorCode eq '{code}'"},
        )
        rows = payload.get("value") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise ValueError("WHO GHO indicator metadata response is invalid")
        matches = [
            row for row in rows
            if isinstance(row, dict)
            and row.get("IndicatorCode") == code
            and row.get("Language") == "EN"
        ]
        if len(matches) != 1:
            raise ValueError(f"WHO GHO metadata is missing or ambiguous for {code}")
        return matches[0]

    def fetch_observations(
        self,
        code: str,
        start_year: int,
        end_year: int,
    ) -> list[dict[str, Any]]:
        spec = WHO_INDICATORS.get(code)
        if spec is None:
            raise ValueError(f"Unsupported WHO GHO indicator: {code}")
        if start_year < 1900 or end_year < start_year or end_year > utc_now().year:
            raise ValueError("Invalid WHO GHO import year range")

        filters = [
            f"TimeDim ge {start_year}",
            f"TimeDim le {end_year}",
            "SpatialDimType eq 'COUNTRY'",
        ]
        filters.extend(f"{key} eq '{value}'" for key, value in spec.dimensions)
        url = f"{WHO_GHO_API_URL}/{code}"
        base_params: dict[str, Any] = {
            "$filter": " and ".join(filters),
            "$top": self.page_size,
        }
        params: dict[str, Any] | None = {**base_params, "$skip": 0}
        results: list[dict[str, Any]] = []
        seen_pages: set[tuple[str, ...]] = set()
        skip_offset = 0
        while url:
            payload = self._get_json(url, params)
            if not isinstance(payload, dict) or not isinstance(payload.get("value"), list):
                raise ValueError("WHO GHO observation response did not contain a row list")
            rows = payload["value"]
            if not all(isinstance(row, dict) for row in rows):
                raise ValueError("WHO GHO response contained an invalid observation row")
            page_fingerprint = tuple(
                str(row.get("Id", json.dumps(row, sort_keys=True)))
                for row in rows
            )
            if rows and page_fingerprint in seen_pages:
                raise ValueError("WHO GHO pagination returned a repeated page")
            if rows:
                seen_pages.add(page_fingerprint)
            results.extend(rows)
            skip_offset += len(rows)
            next_link = payload.get("@odata.nextLink")
            if next_link is not None:
                if not isinstance(next_link, str):
                    raise ValueError("WHO GHO pagination link is invalid")
                parsed = urlsplit(next_link)
                base = urlsplit(WHO_GHO_API_URL)
                if (
                    parsed.scheme != "https"
                    or parsed.netloc != base.netloc
                    or not parsed.path.startswith("/api/")
                ):
                    raise ValueError(
                        "WHO GHO pagination link left the official API origin"
                    )
                url = next_link
                params = None
            elif len(rows) == self.page_size:
                url = f"{WHO_GHO_API_URL}/{code}"
                params = {**base_params, "$skip": skip_offset}
            else:
                url = ""
        return results

    def fetch_country_metadata(
        self,
        country_codes: set[str],
    ) -> list[dict[str, Any]]:
        codes = sorted(
            code for value in country_codes
            if (code := normalize_iso3(value)) is not None
        )
        if not codes:
            return []
        country_filter = " or ".join(
            f"CountryCode eq '{code}'" for code in codes
        )
        payload = self._get_json(
            f"{WHO_GHO_API_URL}/RegionCountry",
            {"$filter": country_filter, "$top": min(1000, len(codes) * 2)},
        )
        rows = payload.get("value") if isinstance(payload, dict) else None
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise ValueError("WHO GHO country metadata response is invalid")
        return [
            row for row in rows
            if row.get("Language") == "EN"
            and row.get("CountryCode") in codes
        ]


def _ensure_who_source(db: Session) -> None:
    statement = sqlite_insert(HealthDataSource).values(
        code=WHO_GHO_SOURCE_CODE,
        name=WHO_GHO_SOURCE_NAME,
        url=WHO_GHO_API_URL,
        updated_at=utc_now(),
    )
    db.execute(
        statement.on_conflict_do_update(
            index_elements=[HealthDataSource.code],
            set_={
                "name": statement.excluded.name,
                "url": statement.excluded.url,
                "updated_at": statement.excluded.updated_at,
            },
        )
    )
    db.commit()


def _upsert_who_countries(
    db: Session,
    client: WhoGhoClient,
    rows: list[dict[str, Any]],
) -> set[str]:
    existing = set(db.scalars(select(HealthCountry.iso3)))
    candidate_codes = {
        code
        for row in rows
        if row.get("SpatialDimType") == "COUNTRY"
        and (code := normalize_iso3(row.get("SpatialDim"))) is not None
    }
    missing = candidate_codes.difference(existing)
    if not missing:
        return existing
    metadata_rows = client.fetch_country_metadata(missing)
    pending: dict[str, dict[str, Any]] = {}
    for row in metadata_rows:
        iso3 = normalize_iso3(row.get("CountryCode"))
        name = row.get("CountryName")
        if (
            iso3 is not None
            and iso3 in missing
            and isinstance(name, str)
            and name.strip()
            and row.get("Language") == "EN"
        ):
            pending[iso3] = {
                "iso3": iso3,
                "iso2": None,
                "name": name.strip(),
                "region": row.get("RegionName") or None,
                "income_level": None,
                "updated_at": utc_now(),
            }
    if pending:
        statement = sqlite_insert(HealthCountry).values(list(pending.values()))
        db.execute(
            statement.on_conflict_do_nothing(index_elements=[HealthCountry.iso3])
        )
        db.commit()
        existing.update(pending)
    return existing


def _upsert_who_indicator(
    db: Session,
    code: str,
    provider_name: str,
) -> None:
    spec = WHO_INDICATORS[code]
    if " ".join(provider_name.split()) != " ".join(spec.name.split()):
        raise ValueError(f"WHO GHO indicator name did not match the approved catalog for {code}")
    statement = sqlite_insert(HealthIndicator).values(
        code=code,
        name=provider_name.strip(),
        definition=spec.definition,
        unit=spec.unit,
        source_code=WHO_GHO_SOURCE_CODE,
        publisher=spec.publisher,
        definition_url=WHO_INDICATOR_REGISTRY_URL,
        dataset_code=code,
        dataset_name=spec.dataset_name,
        dataset_version=None,
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
                "publisher": statement.excluded.publisher,
                "definition_url": statement.excluded.definition_url,
                "dataset_code": statement.excluded.dataset_code,
                "dataset_name": statement.excluded.dataset_name,
                "dataset_version": statement.excluded.dataset_version,
                "updated_at": statement.excluded.updated_at,
            },
        )
    )
    db.flush()


def _choose_duplicate(
    previous: dict[str, Any],
    candidate: dict[str, Any],
    code: str,
) -> dict[str, Any]:
    same_measurement = all(
        previous[field] == candidate[field]
        for field in ("value", "unit", "dimensions_json", "uncertainty_lower", "uncertainty_upper")
    )
    previous_timestamp = previous["source_record_timestamp"]
    candidate_timestamp = candidate["source_record_timestamp"]
    if not same_measurement and (
        previous_timestamp is None
        or candidate_timestamp is None
        or previous_timestamp == candidate_timestamp
    ):
        raise ValueError(
            f"Conflicting duplicate WHO rows without a decisive source timestamp for {code}"
        )
    if (
        candidate_timestamp is not None
        and (previous_timestamp is None or candidate_timestamp > previous_timestamp)
    ):
        return candidate
    return previous


def ingest_who_gho(
    db: Session,
    start_year: int,
    end_year: int,
    indicator_codes: list[str] | None = None,
    client: WhoGhoClient | None = None,
) -> list[HealthDataImport]:
    if start_year < 1900 or end_year < start_year or end_year > utc_now().year:
        raise ValueError("Invalid WHO GHO import year range")
    codes = indicator_codes or list(WHO_INDICATORS)
    unsupported = set(codes).difference(WHO_INDICATORS)
    if unsupported:
        raise ValueError(f"Unsupported WHO GHO indicators: {', '.join(sorted(unsupported))}")
    if len(set(codes)) != len(codes):
        raise ValueError("WHO GHO indicator codes must be unique")

    ensure_health_data_schema(db.get_bind())
    _ensure_who_source(db)
    client = client or WhoGhoClient()
    imports: list[HealthDataImport] = []
    for code in codes:
        run = HealthDataImport(
            source_code=WHO_GHO_SOURCE_CODE,
            indicator_code=code,
            status="running",
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        try:
            metadata = client.fetch_indicator(code)
            provider_name = metadata.get("IndicatorName")
            if not isinstance(provider_name, str) or not provider_name.strip():
                raise ValueError(f"WHO GHO indicator name is missing for {code}")
            _upsert_who_indicator(db, code, provider_name)
            db.commit()

            rows = client.fetch_observations(code, start_year, end_year)
            run.rows_received = len(rows)
            known_countries = _upsert_who_countries(db, client, rows)
            pending: dict[tuple[str, int], dict[str, Any]] = {}
            for row in rows:
                try:
                    parsed = parse_gho_observation(code, row, start_year, end_year)
                    if parsed is None:
                        run.rows_missing += 1
                        continue
                    key, observation = parsed
                    if key[0] not in known_countries:
                        raise ValueError(
                            f"Country code {key[0]} is not in the local country catalog"
                        )
                except ValueError as exc:
                    run.rows_rejected += 1
                    logger.warning("Skipping invalid WHO GHO row for %s: %s", code, exc)
                    continue
                if key in pending:
                    run.rows_duplicate += 1
                    pending[key] = _choose_duplicate(pending[key], observation, code)
                else:
                    pending[key] = observation

            if run.rows_received == 0:
                raise ValueError(f"WHO GHO returned no observations for {code}")
            if not pending:
                raise ValueError(f"WHO GHO had no valid observations for {code}")

            upsert_observation_batch(db, code, pending, run)
            run.status = "success"
            run.completed_at = utc_now()
            run.error_message = None
            db.commit()
            imports.append(run)
            logger.info(
                "Imported WHO GHO indicator %s: %d inserted, %d updated, "
                "%d missing, %d rejected, %d duplicates",
                code,
                run.rows_inserted,
                run.rows_updated,
                run.rows_missing,
                run.rows_rejected,
                run.rows_duplicate,
            )
        except Exception as exc:
            db.rollback()
            failed_run = db.get(HealthDataImport, run.id)
            if failed_run is not None:
                failed_run.status = "failed"
                failed_run.completed_at = utc_now()
                failed_run.error_message = str(exc)[:2000]
                db.commit()
            logger.exception("WHO GHO import failed for %s", code)
            raise
    return imports
