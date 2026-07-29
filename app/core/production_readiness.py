import json

from app.core.config import (
    ADMIN_API_KEY,
    ADMIN_CREDENTIALS_JSON,
    ALLOW_SYNTHETIC_PRICING,
    APP_DEBUG,
    APP_ENV,
    CLIENT_CREDENTIALS_JSON,
)
from app.infrastructure.database import DATABASE_URL


class UnsafeProductionConfiguration(RuntimeError):
    pass


def production_configuration_errors() -> list[str]:
    if APP_ENV.lower() not in {"production", "prod"}:
        return []

    errors: list[str] = []
    if APP_DEBUG:
        errors.append("APP_DEBUG must be false")
    if ALLOW_SYNTHETIC_PRICING:
        errors.append("ALLOW_SYNTHETIC_PRICING must be false")
    if DATABASE_URL.startswith("sqlite"):
        errors.append("DATABASE_URL must use the production PostgreSQL database")
    if ADMIN_API_KEY:
        errors.append("legacy ADMIN_API_KEY is forbidden; use ADMIN_CREDENTIALS_JSON")
    _validate_credentials_json(
        ADMIN_CREDENTIALS_JSON,
        "ADMIN_CREDENTIALS_JSON",
        errors,
    )
    _validate_credentials_json(
        CLIENT_CREDENTIALS_JSON,
        "CLIENT_CREDENTIALS_JSON",
        errors,
    )
    return errors


def assert_safe_production_configuration() -> None:
    errors = production_configuration_errors()
    if errors:
        raise UnsafeProductionConfiguration(
            "Unsafe production configuration: " + "; ".join(errors)
        )


def _validate_credentials_json(
    value: str,
    name: str,
    errors: list[str],
) -> None:
    try:
        credentials = json.loads(value)
    except json.JSONDecodeError:
        errors.append(f"{name} must be valid JSON")
        return
    if not isinstance(credentials, dict) or not credentials:
        errors.append(f"{name} must contain at least one credential")
        return
    if any(
        not isinstance(actor, str)
        or not actor.strip()
        or not isinstance(key, str)
        or len(key) < 24
        for actor, key in credentials.items()
    ):
        errors.append(f"{name} contains an invalid or short credential")
