from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database.database import Base
from app.utils.datetime_utils import utc_now


class HealthCountry(Base):
    __tablename__ = "health_countries"

    iso3 = Column(String(3), primary_key=True)
    iso2 = Column(String(2), nullable=True, index=True)
    name = Column(String, nullable=False)
    region = Column(String, nullable=True)
    income_level = Column(String, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=utc_now)
    observations = relationship("HealthIndicatorObservation", back_populates="country")


class HealthDataSource(Base):
    __tablename__ = "health_data_sources"

    code = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=utc_now)
    observations = relationship("HealthIndicatorObservation", back_populates="source")


class HealthIndicator(Base):
    __tablename__ = "health_indicators"

    code = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    definition = Column(String, nullable=False)
    unit = Column(String, nullable=False)
    source_code = Column(
        String,
        ForeignKey("health_data_sources.code"),
        nullable=False,
    )
    publisher = Column(Text, nullable=True)
    definition_url = Column(Text, nullable=True)
    dataset_code = Column(String, nullable=True)
    dataset_name = Column(Text, nullable=True)
    dataset_version = Column(String, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=utc_now)
    observations = relationship("HealthIndicatorObservation", back_populates="indicator")


class HealthIndicatorObservation(Base):
    __tablename__ = "health_indicator_observations"
    __table_args__ = (
        UniqueConstraint(
            "country_iso3",
            "indicator_code",
            "year",
            name="uq_health_observation_country_indicator_year",
        ),
        Index("ix_health_observation_indicator_year", "indicator_code", "year"),
    )

    id = Column(Integer, primary_key=True)
    country_iso3 = Column(
        String(3),
        ForeignKey("health_countries.iso3"),
        nullable=False,
    )
    indicator_code = Column(
        String,
        ForeignKey("health_indicators.code"),
        nullable=False,
    )
    value = Column(Float, nullable=False)
    year = Column(Integer, nullable=False)
    unit = Column(String, nullable=False)
    source_code = Column(
        String,
        ForeignKey("health_data_sources.code"),
        nullable=False,
    )
    imported_at = Column(DateTime, nullable=False, default=utc_now)
    source_reference = Column(Text, nullable=True)
    source_publication_date = Column(DateTime, nullable=True)
    source_record_timestamp = Column(DateTime, nullable=True)
    source_value_text = Column(Text, nullable=True)
    denominator_value = Column(Float, nullable=True)
    denominator_definition = Column(Text, nullable=True)
    dimensions_json = Column(Text, nullable=True)
    uncertainty_lower = Column(Float, nullable=True)
    uncertainty_upper = Column(Float, nullable=True)
    estimate_status = Column(String, nullable=True)
    country = relationship("HealthCountry", back_populates="observations")
    indicator = relationship("HealthIndicator", back_populates="observations")
    source = relationship("HealthDataSource", back_populates="observations")


class HealthIndicatorObservationRevision(Base):
    __tablename__ = "health_indicator_observation_revisions"

    id = Column(Integer, primary_key=True)
    observation_id = Column(
        Integer,
        ForeignKey("health_indicator_observations.id"),
        nullable=False,
        index=True,
    )
    changed_at = Column(DateTime, nullable=False, default=utc_now)
    previous_value = Column(Float, nullable=False)
    previous_unit = Column(String, nullable=False)
    previous_source_code = Column(String, nullable=False)
    previous_imported_at = Column(DateTime, nullable=False)
    previous_provenance_json = Column(Text, nullable=False)


class HealthDataImport(Base):
    __tablename__ = "health_data_imports"

    id = Column(Integer, primary_key=True)
    source_code = Column(
        String,
        ForeignKey("health_data_sources.code"),
        nullable=False,
    )
    indicator_code = Column(
        String,
        ForeignKey("health_indicators.code"),
        nullable=True,
    )
    started_at = Column(DateTime, nullable=False, default=utc_now)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, nullable=False)
    rows_received = Column(Integer, nullable=False, default=0)
    rows_inserted = Column(Integer, nullable=False, default=0)
    rows_updated = Column(Integer, nullable=False, default=0)
    rows_missing = Column(Integer, nullable=False, default=0)
    rows_rejected = Column(Integer, nullable=False, default=0)
    rows_duplicate = Column(Integer, nullable=False, default=0)
    error_message = Column(String, nullable=True)


class HealthDataImportCheckpoint(Base):
    __tablename__ = "health_data_import_checkpoints"
    __table_args__ = (
        UniqueConstraint(
            "indicator_code",
            "country_key",
            "start_year",
            "end_year",
            "page",
            name="uq_health_import_checkpoint",
        ),
    )

    id = Column(Integer, primary_key=True)
    indicator_code = Column(String, ForeignKey("health_indicators.code"), nullable=False)
    country_key = Column(String(3), nullable=False, default="")
    start_year = Column(Integer, nullable=False)
    end_year = Column(Integer, nullable=False)
    page_size = Column(Integer, nullable=False)
    page = Column(Integer, nullable=False)
    pages_total = Column(Integer, nullable=False)
    completed_at = Column(DateTime, nullable=False, default=utc_now)
