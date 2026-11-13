import os
from urllib.parse import urlsplit


_DEVELOPMENT_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
)
_DEVELOPMENT_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1):517[0-9]$"


def get_cors_settings(
    environment: str | None = None,
    configured_origins: str | None = None,
) -> tuple[list[str], str | None]:
    deployment = (
        environment
        if environment is not None
        else os.getenv("HEALTHSCOPE_ENV", "development")
    ).strip().lower()
    if deployment not in {"development", "production"}:
        raise ValueError("HEALTHSCOPE_ENV must be development or production")

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
