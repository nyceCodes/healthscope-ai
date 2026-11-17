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