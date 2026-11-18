from sqlalchemy import create_engine, inspect, text

from app.database.database import ensure_health_data_schema


def test_health_data_schema_adds_provenance_fields_idempotently():
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE TABLE health_indicators "
                    "(code TEXT PRIMARY KEY, source_code TEXT)"
                )
            )
            connection.execute(
                text(
                    "CREATE TABLE health_indicator_observations ("
                    "id INTEGER PRIMARY KEY, country_iso3 TEXT, "
                    "indicator_code TEXT, source_code TEXT)"
                )
            )
            connection.execute(
                text(
                    "CREATE TABLE health_data_imports "
                    "(id INTEGER PRIMARY KEY)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO health_indicators (code, source_code) "
                    "VALUES ('SP.POP.TOTL', 'world-bank-wdi')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO health_indicator_observations "
                    "(id, country_iso3, indicator_code, source_code) "
                    "VALUES (1, 'PHL', 'SP.POP.TOTL', 'world-bank-wdi')"
                )
            )

        ensure_health_data_schema(engine)
        ensure_health_data_schema(engine)

        inspector = inspect(engine)
        indicator_columns = {
            column["name"] for column in inspector.get_columns("health_indicators")
        }
        observation_columns = {
            column["name"]
            for column in inspector.get_columns("health_indicator_observations")
        }
        import_columns = {
            column["name"] for column in inspector.get_columns("health_data_imports")
        }
        assert {"publisher", "definition_url", "dataset_code", "dataset_name"} <= indicator_columns
        assert {
            "source_reference",
            "source_record_timestamp",
            "source_publication_date",
            "denominator_value",
            "dimensions_json",
            "uncertainty_lower",
            "uncertainty_upper",
        } <= observation_columns
        assert "rows_duplicate" in import_columns

        with engine.connect() as connection:
            indicator = connection.execute(
                text("SELECT publisher, dataset_code FROM health_indicators")
            ).one()
            observation = connection.execute(
                text(
                    "SELECT source_reference, dimensions_json, estimate_status "
                    "FROM health_indicator_observations"
                )
            ).one()
        assert "historical original producer not captured" in indicator.publisher
        assert indicator.dataset_code == "WDI"
        assert observation.dimensions_json == "{}"
        assert observation.estimate_status == "legacy_method_not_recorded"
        assert observation.source_reference.endswith("SP.POP.TOTL?format=json")
    finally:
        engine.dispose()
