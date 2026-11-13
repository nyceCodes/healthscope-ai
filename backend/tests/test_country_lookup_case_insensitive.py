from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.models.country_snapshot import CountrySnapshot
from app.models.life_expectancy import LifeExpectancy
from app.services.country_report_service import CountryReportService
from app.services.life_expectancy_service import LifeExpectancyService


def test_life_expectancy_service_matches_country_case_insensitively():
    engine = create_engine("sqlite://")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        db.add(
            LifeExpectancy(
                country="Philippines",
                year=2015,
                status="Developing",
                life_expectancy=69.2,
                adult_mortality=95.5,
                bmi=25.1,
                gdp=3200.0,
                schooling=10.8,
                population=110.2,
            )
        )
        db.commit()

        record = LifeExpectancyService.latest_country_record(db, "philippines")
        assert record is not None
        assert record.country == "Philippines"
        assert record.life_expectancy == 69.2
    finally:
        db.close()


def test_country_report_service_matches_case_insensitively():
    engine = create_engine("sqlite://")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        db.add(
            CountrySnapshot(
                country="Philippines",
                population=110_000_000,
                cases=100,
                deaths=10,
                recovered=80,
                active=10,
                tests=200,
                recovery_rate=80.0,
                mortality_rate=10.0,
                health_index=72.3,
            )
        )
        db.add(
            LifeExpectancy(
                country="Philippines",
                year=2015,
                status="Developing",
                life_expectancy=69.2,
                adult_mortality=95.5,
                bmi=25.1,
                gdp=3200.0,
                schooling=10.8,
                population=110.2,
            )
        )
        db.commit()

        snapshot, life_record, top_country = CountryReportService.build_report(db, "PHILIPPINES")
        assert snapshot is not None
        assert snapshot.country == "Philippines"
        assert life_record is not None
        assert life_record.country == "Philippines"
        assert top_country is None or top_country.country is not None
    finally:
        db.close()
