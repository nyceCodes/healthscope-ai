import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy import text

from app.database.database import assert_no_prediction_history
from scripts.create_production_seed import create_production_seed


def create_test_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE health_indicator_observations (id INTEGER PRIMARY KEY);
            CREATE TABLE country_snapshots (id INTEGER PRIMARY KEY);
            CREATE TABLE prediction_history (id INTEGER PRIMARY KEY);
            CREATE TABLE nutrition_searches (id INTEGER PRIMARY KEY);
            CREATE TABLE health_data_imports (id INTEGER PRIMARY KEY);
            CREATE TABLE health_data_import_checkpoints (id INTEGER PRIMARY KEY);
            INSERT INTO health_indicator_observations VALUES (1), (2);
            INSERT INTO country_snapshots VALUES (1);
            INSERT INTO prediction_history VALUES (1);
            INSERT INTO nutrition_searches VALUES (1);
            INSERT INTO health_data_imports VALUES (1);
            INSERT INTO health_data_import_checkpoints VALUES (1);
            """
        )


def test_seed_preserves_public_data_and_excludes_local_records(tmp_path):
    source = tmp_path / "source.db"
    output = tmp_path / "deployment" / "healthscope.db"
    create_test_database(source)

    report = create_production_seed(source, output)

    assert report == {"observations": 2, "excluded_predictions": 1}
    with sqlite3.connect(source) as source_db:
        assert source_db.execute("SELECT COUNT(*) FROM prediction_history").fetchone()[0] == 1
    with sqlite3.connect(output) as seed_db:
        assert seed_db.execute(
            "SELECT COUNT(*) FROM health_indicator_observations"
        ).fetchone()[0] == 2
        assert seed_db.execute("SELECT COUNT(*) FROM country_snapshots").fetchone()[0] == 1
        for table in (
            "prediction_history",
            "nutrition_searches",
            "health_data_imports",
            "health_data_import_checkpoints",
        ):
            assert seed_db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0] == 0
    seed_engine = create_engine(f"sqlite:///{output.as_posix()}")
    try:
        assert_no_prediction_history(seed_engine)
    finally:
        seed_engine.dispose()


def test_seed_cannot_replace_the_source_database(tmp_path):
    source = tmp_path / "source.db"
    create_test_database(source)

    with pytest.raises(ValueError, match="must not replace"):
        create_production_seed(source, source)


def test_packaged_production_seed_is_complete_and_sanitized():
    seed_path = Path(__file__).resolve().parents[1] / "deployment" / "healthscope.db"

    with sqlite3.connect(f"{seed_path.as_uri()}?mode=ro", uri=True) as seed_db:
        assert seed_db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert seed_db.execute(
            "SELECT COUNT(*) FROM health_indicator_observations"
        ).fetchone()[0] == 47_303
        assert seed_db.execute(
            "SELECT COUNT(*) FROM health_indicators"
        ).fetchone()[0] == 10
        assert {
            row[0]
            for row in seed_db.execute("SELECT code FROM health_indicators")
        } == {
            "MDG_0000000020",
            "MDG_0000000025",
            "MDG_0000000026",
            "SH.DYN.MORT",
            "SH.XPD.CHEX.GD.ZS",
            "SP.DYN.LE00.IN",
            "SP.POP.TOTL",
            "UHC_INDEX_REPORTED",
            "WHOSIS_000003",
            "WHS4_100",
        }
        assert seed_db.execute(
            "SELECT COUNT(*) FROM health_countries"
        ).fetchone()[0] == 221
        assert seed_db.execute(
            "SELECT COUNT(*) FROM health_data_sources"
        ).fetchone()[0] == 2
        assert seed_db.execute(
            "SELECT COUNT(*) FROM health_data_imports"
        ).fetchone()[0] == 0
        assert seed_db.execute(
            "SELECT COUNT(*) FROM prediction_history"
        ).fetchone()[0] == 0
        assert seed_db.execute(
            "SELECT COUNT(*) FROM country_snapshots"
        ).fetchone()[0] == 38
        assert seed_db.execute(
            "SELECT COUNT(*) FROM life_expectancy"
        ).fetchone()[0] == 2_938
        assert seed_db.execute(
            "SELECT COUNT(*) FROM prediction_history"
        ).fetchone()[0] == 0


def test_production_database_guard_rejects_local_history(tmp_path):
    database_path = tmp_path / "dirty.db"
    engine = create_engine(f"sqlite:///{database_path}")
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE prediction_history (id INTEGER)"))
            connection.execute(text("INSERT INTO prediction_history VALUES (1)"))

        with pytest.raises(RuntimeError, match="prediction-history"):
            assert_no_prediction_history(engine)
    finally:
        engine.dispose()
