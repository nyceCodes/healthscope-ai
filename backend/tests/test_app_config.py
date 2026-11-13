import pytest

from app.config import get_cors_settings


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
