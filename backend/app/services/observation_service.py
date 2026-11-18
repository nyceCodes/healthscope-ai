import json
from datetime import date, datetime
from typing import Any

from sqlalchemy import select, tuple_
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.models.health_indicator import (
    HealthDataImport,
    HealthIndicatorObservation,
    HealthIndicatorObservationRevision,
)
from app.utils.datetime_utils import utc_now


_PROVENANCE_FIELDS = (
    "source_reference",
    "source_publication_date",
    "source_record_timestamp",
    "source_value_text",
    "denominator_value",
    "denominator_definition",
    "dimensions_json",
    "uncertainty_lower",
    "uncertainty_upper",
    "estimate_status",
)


def decode_dimensions(value: str | None) -> dict[str, str] | None:
    if value is None:
        return None
    decoded = json.loads(value)
    if not isinstance(decoded, dict) or not all(
        isinstance(key, str) and isinstance(item, str)
        for key, item in decoded.items()
    ):
        raise ValueError("Stored observation dimensions are invalid")
    return decoded


def _serialize_provenance(observation: HealthIndicatorObservation) -> str:
    values: dict[str, Any] = {}
    for field in _PROVENANCE_FIELDS:
        value = getattr(observation, field)
        values[field] = value.isoformat() if isinstance(value, (date, datetime)) else value
    return json.dumps(values, sort_keys=True, separators=(",", ":"))


def upsert_observation_batch(
    db: Session,
    code: str,
    observations: dict[tuple[str, int], dict[str, Any]],
    run: HealthDataImport,
) -> None:
    if not observations:
        return

    keys = list(observations)
    existing: dict[tuple[str, int], HealthIndicatorObservation] = {}
    for offset in range(0, len(keys), 400):
        batch = keys[offset : offset + 400]
        rows = db.scalars(
            select(HealthIndicatorObservation).where(
                HealthIndicatorObservation.indicator_code == code,
                tuple_(
                    HealthIndicatorObservation.country_iso3,
                    HealthIndicatorObservation.year,
                ).in_(batch),
            )
        )
        existing.update({(row.country_iso3, row.year): row for row in rows})

    run.rows_updated += len(existing)
    run.rows_inserted += len(keys) - len(existing)
    for key, previous in existing.items():
        incoming = observations[key]
        has_changed = (
            previous.value != incoming["value"]
            or previous.unit != incoming["unit"]
            or previous.source_code != incoming["source_code"]
            or any(
                getattr(previous, field) != incoming.get(field)
                for field in _PROVENANCE_FIELDS
            )
        )
        if has_changed:
            db.add(
                HealthIndicatorObservationRevision(
                    observation_id=previous.id,
                    changed_at=utc_now(),
                    previous_value=previous.value,
                    previous_unit=previous.unit,
                    previous_source_code=previous.source_code,
                    previous_imported_at=previous.imported_at,
                    previous_provenance_json=_serialize_provenance(previous),
                )
            )

    excluded = sqlite_insert(HealthIndicatorObservation).excluded
    update_fields = {
        "value": excluded.value,
        "unit": excluded.unit,
        "source_code": excluded.source_code,
        "imported_at": excluded.imported_at,
        **{field: getattr(excluded, field) for field in _PROVENANCE_FIELDS},
    }
    values = list(observations.values())
    for offset in range(0, len(values), 300):
        db.execute(
            sqlite_insert(HealthIndicatorObservation)
            .values(values[offset : offset + 300])
            .on_conflict_do_update(
                index_elements=[
                    HealthIndicatorObservation.country_iso3,
                    HealthIndicatorObservation.indicator_code,
                    HealthIndicatorObservation.year,
                ],
                set_=update_fields,
            )
        )
