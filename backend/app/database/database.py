from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base

from app.config import get_database_path


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[2] / "healthscope.db"
DATABASE_PATH = get_database_path(DEFAULT_DATABASE_PATH)
DATABASE_URL = URL.create("sqlite", database=str(DATABASE_PATH))

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def assert_no_prediction_history(database_engine) -> None:
    table_name = "prediction_history"
    with database_engine.connect() as connection:
        table_names = set(inspect(connection).get_table_names())
        if table_name in table_names:
            row_count = connection.execute(
                text(f'SELECT COUNT(*) FROM "{table_name}"')
            ).scalar_one()
            if row_count:
                raise RuntimeError(
                    "Production SQLite database contains local prediction-history "
                    "records; rebuild it with scripts.create_production_seed"
                )


def ensure_health_data_schema(database_engine) -> None:
    additions = {
        "health_indicators": {
            "publisher": "TEXT",
            "definition_url": "TEXT",
            "dataset_code": "VARCHAR",
            "dataset_name": "TEXT",
            "dataset_version": "VARCHAR",
        },
        "health_indicator_observations": {
            "source_reference": "TEXT",
            "source_publication_date": "DATETIME",
            "source_record_timestamp": "DATETIME",
            "source_value_text": "TEXT",
            "denominator_value": "FLOAT",
            "denominator_definition": "TEXT",
            "dimensions_json": "TEXT",
            "uncertainty_lower": "FLOAT",
            "uncertainty_upper": "FLOAT",
            "estimate_status": "VARCHAR",
        },
        "health_data_imports": {"rows_duplicate": "INTEGER NOT NULL DEFAULT 0"},
    }

    with database_engine.begin() as connection:
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        for table_name, columns in additions.items():
            if table_name not in tables:
                continue
            existing_columns = {
                column["name"] for column in inspector.get_columns(table_name)
            }
            for column_name, column_type in columns.items():
                if column_name not in existing_columns:
                    connection.execute(
                        text(
                            f'ALTER TABLE "{table_name}" '
                            f'ADD COLUMN "{column_name}" {column_type}'
                        )
                    )

        if "health_indicators" in tables:
            connection.execute(
                text(
                    "UPDATE health_indicators SET "
                    "publisher = 'World Bank WDI (distribution source; historical "
                    "original producer not captured)', "
                    "definition_url = 'https://api.worldbank.org/v2/indicator/' "
                    "|| code || '?format=json', "
                    "dataset_code = 'WDI', "
                    "dataset_name = 'World Development Indicators' "
                    "WHERE code IN ('SP.DYN.LE00.IN', 'SP.POP.TOTL', "
                    "'SH.DYN.MORT', 'SH.XPD.CHEX.GD.ZS') "
                    "AND publisher IS NULL"
                )
            )
        if "health_indicator_observations" in tables:
            connection.execute(
                text(
                    "UPDATE health_indicator_observations SET "
                    "source_reference = 'https://api.worldbank.org/v2/country/' "
                    "|| country_iso3 || '/indicator/' || indicator_code || '?format=json', "
                    "dimensions_json = '{}', "
                    "estimate_status = 'legacy_method_not_recorded' "
                    "WHERE source_code = 'world-bank-wdi' "
                    "AND source_reference IS NULL"
                )
            )
        if "health_data_sources" in tables:
            connection.execute(
                text(
                    "UPDATE health_data_sources SET "
                    "name = 'World Bank — World Development Indicators' "
                    "WHERE code = 'world-bank-wdi' AND "
                    "name = 'World Bank \ufffd World Development Indicators' "
                )
            )