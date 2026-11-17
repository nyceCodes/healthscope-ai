from pathlib import Path

import pytest

from app.config import (
    get_cors_settings,
    get_database_path,
    get_prediction_history_enabled,
)


def test_development_cors_has_localhost_defaults_and_port_fallback():
    origins, origin_regex = get_cors_settings("development", None)

    assert "http://localhost:5173" in origins
    assert origin_regex == r"^https?://(localhost|127\.0\.0\.1):517[0-9]$"


def test_production_cors_requires_explicit_trusted_origins():
    with pytest.raises(ValueError, match="HEALTHSCOPE_CORS_ORIGINS"):
        get_cors_settings("production", None)

    origins, origin_regex = get_cors_settings(
        "production",
        "https://healthscope.example,https://www.healthscope.example",
    )
    assert origins == [
        "https://healthscope.example",
        "https://www.healthscope.example",
    ]
    assert origin_regex is None


def test_cors_rejects_non_origin_urls():
    with pytest.raises(ValueError, match="without paths"):
        get_cors_settings("production", "https://healthscope.example/api")


def test_prediction_history_is_local_by_default_and_configurable():
    assert get_prediction_history_enabled("development", None) is True
    assert get_prediction_history_enabled("development", "false") is False
    assert get_prediction_history_enabled("development", "true") is True


def test_prediction_history_is_always_disabled_in_production():
    assert get_prediction_history_enabled("production", None) is False
    assert get_prediction_history_enabled("production", "true") is False
    assert get_prediction_history_enabled("production", "false") is False


def test_prediction_history_rejects_invalid_setting():
    with pytest.raises(ValueError, match="must be a boolean"):
        get_prediction_history_enabled("development", "sometimes")


def test_production_database_path_requires_an_initialized_separate_file(tmp_path):
    local_database = tmp_path / "healthscope.db"
    seed_database = tmp_path / "production.db"
    seed_database.touch()

    with pytest.raises(ValueError, match="HEALTHSCOPE_DATABASE_PATH"):
        get_database_path(local_database, "production", None)
    with pytest.raises(ValueError, match="absolute path"):
        get_database_path(local_database, "production", "production.db")
    with pytest.raises(ValueError, match="local HealthScope database"):
        get_database_path(local_database, "production", str(local_database))
    assert get_database_path(
        local_database,
        "production",
        str(seed_database),
    ) == seed_database.resolve()
    assert get_database_path(local_database, "development", None) == Path(
        local_database
    ).resolve()
