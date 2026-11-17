import os
from pathlib import Path
from urllib.parse import urlsplit


_DEVELOPMENT_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
)
_DEVELOPMENT_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1):517[0-9]$"


def _get_deployment_environment(environment: str | None = None) -> str:
    deployment = (
        environment
        if environment is not None
        else os.getenv("HEALTHSCOPE_ENV", "development")
    ).strip().lower()
    if deployment not in {"development", "production"}:
        raise ValueError("HEALTHSCOPE_ENV must be development or production")
    return deployment


def get_cors_settings(
    environment: str | None = None,
    configured_origins: str | None = None,
) -> tuple[list[str], str | None]:
    deployment = _get_deployment_environment(environment)

    raw_origins = (
        configured_origins
        if configured_origins is not None
        else os.getenv("HEALTHSCOPE_CORS_ORIGINS")
    )
    origins = (
        [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
        if raw_origins
        else list(_DEVELOPMENT_ORIGINS)
        if deployment == "development"
        else []
    )
    if not origins:
        raise ValueError(
            "Set HEALTHSCOPE_CORS_ORIGINS to one or more trusted origins in production"
        )

    for origin in origins:
        parsed = urlsplit(origin)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
        ):
            raise ValueError(
                "HEALTHSCOPE_CORS_ORIGINS entries must be HTTP(S) origins without paths"
            )

    origin_regex = (
        _DEVELOPMENT_ORIGIN_REGEX
        if deployment == "development" and not raw_origins
        else None
    )
    return origins, origin_regex


def get_prediction_history_enabled(
    environment: str | None = None,
    configured_enabled: str | None = None,
) -> bool:
    deployment = _get_deployment_environment(environment)
    raw_enabled = (
        configured_enabled
        if configured_enabled is not None
        else os.getenv("HEALTHSCOPE_PREDICTION_HISTORY_ENABLED")
    )

    enabled = None
    if raw_enabled is not None:
        normalized = raw_enabled.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            enabled = True
        elif normalized in {"0", "false", "no", "off"}:
            enabled = False
        else:
            raise ValueError(
                "HEALTHSCOPE_PREDICTION_HISTORY_ENABLED must be a boolean value"
            )

    if deployment == "production":
        return False
    return True if enabled is None else enabled


def get_database_path(
    default_path: Path,
    environment: str | None = None,
    configured_path: str | None = None,
) -> Path:
    deployment = _get_deployment_environment(environment)
    raw_path = (
        configured_path
        if configured_path is not None
        else os.getenv("HEALTHSCOPE_DATABASE_PATH")
    )

    if deployment == "production" and not raw_path:
        raise ValueError(
            "Set HEALTHSCOPE_DATABASE_PATH to the sanitized production database"
        )

    path = Path(raw_path).expanduser() if raw_path else default_path
    if deployment == "production":
        if not path.is_absolute():
            raise ValueError("HEALTHSCOPE_DATABASE_PATH must be an absolute path")
        if path.resolve() == default_path.resolve():
            raise ValueError(
                "Production cannot use the local HealthScope database"
            )
        if not path.is_file():
            raise ValueError(
                "HEALTHSCOPE_DATABASE_PATH must point to an initialized database file"
            )

    return path.resolve()
