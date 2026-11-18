import string

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.models.health_indicator import (
    HealthDataImport,
    HealthIndicatorObservation,
)
from app.services.observation_service import upsert_observation_batch
from app.utils.datetime_utils import utc_now


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


def _iso3(index: int) -> str:
    alphabet = string.ascii_uppercase
    return (
        alphabet[index // (26 * 26) % 26]
        + alphabet[index // 26 % 26]
        + alphabet[index % 26]
    )


def test_observation_upserts_are_chunked_below_sqlite_parameter_limit(db):
    observations = {}
    for index in range(600):
        country = _iso3(index)
        observations[(country, 2020)] = {
            "country_iso3": country,
            "indicator_code": "TEST_SERIES",
            "year": 2020,
            "value": float(index),
            "unit": "test units",
            "source_code": "test-source",
            "imported_at": utc_now(),
            "source_reference": None,
            "source_publication_date": None,
            "source_record_timestamp": None,
            "source_value_text": None,
            "denominator_value": None,
            "denominator_definition": None,
            "dimensions_json": "{}",
            "uncertainty_lower": None,
            "uncertainty_upper": None,
            "estimate_status": None,
        }

    run = HealthDataImport(source_code="test-source", status="running")
    db.add(run)
    db.commit()
    upsert_observation_batch(db, "TEST_SERIES", observations, run)
    db.commit()

    assert run.rows_inserted == 600
    assert db.scalar(
        select(func.count()).select_from(HealthIndicatorObservation)
    ) == 600
