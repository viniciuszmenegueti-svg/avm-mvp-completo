import json
import re

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from app.core.config import (
    ADMIN_API_KEY,
    ADMIN_CREDENTIALS_JSON,
    ALLOW_SYNTHETIC_PRICING,
    APP_DEBUG,
    APP_ENV,
    CLIENT_CREDENTIALS_JSON,
    MODEL_EXECUTION_MODE,
)
from app.infrastructure.database import DATABASE_URL


class UnsafeProductionConfiguration(RuntimeError):
    pass


DEVELOPMENT_ENVIRONMENTS = frozenset({"development", "dev", "test"})
SECURE_ENVIRONMENTS = frozenset({"homologation", "staging", "production", "prod"})
KNOWN_ENVIRONMENTS = DEVELOPMENT_ENVIRONMENTS | SECURE_ENVIRONMENTS
KNOWN_EXECUTION_MODES = frozenset(
    {"DEMONSTRATION", "HOMOLOGATION_SHADOW", "CONTRACTUAL"}
)
CONTRACTUAL_MODE_BLOCKED_ERROR = (
    "MODEL_EXECUTION_MODE CONTRACTUAL is blocked until the formal external gates "
    "are implemented and evidenced: CAIXA API validation, city/model report, "
    "paired validation, qualified electronic signature and explicit authorization"
)
_PLACEHOLDER_SECRETS = frozenset(
    {
        "admin",
        "admin123",
        "avm_app",
        "change_me",
        "changeme",
        "default",
        "password",
        "password123",
        "postgres",
        "secret",
        "test",
        "test123",
    }
)
_PLACEHOLDER_PREFIXES = (
    "change_this_",
    "example_",
    "replace_with_",
    "your_",
)


def production_configuration_errors() -> list[str]:
    environment = APP_ENV.strip().lower()
    if environment not in KNOWN_ENVIRONMENTS:
        return ["APP_ENV must be one of: " + ", ".join(sorted(KNOWN_ENVIRONMENTS))]
    if MODEL_EXECUTION_MODE not in KNOWN_EXECUTION_MODES:
        return [
            "MODEL_EXECUTION_MODE must be one of: "
            + ", ".join(sorted(KNOWN_EXECUTION_MODES))
        ]
    errors: list[str] = []
    if MODEL_EXECUTION_MODE == "CONTRACTUAL":
        # Este bloqueio não possui chave de liberação local deliberadamente.
        # Os marcos dependem de evidência e autorização externas à aplicação.
        errors.append(CONTRACTUAL_MODE_BLOCKED_ERROR)
    if environment in DEVELOPMENT_ENVIRONMENTS:
        return errors

    if APP_DEBUG:
        errors.append("APP_DEBUG must be false")
    if ALLOW_SYNTHETIC_PRICING:
        errors.append("ALLOW_SYNTHETIC_PRICING must be false")
    if environment in {"homologation", "staging"} and (
        MODEL_EXECUTION_MODE != "HOMOLOGATION_SHADOW"
    ):
        errors.append(
            "MODEL_EXECUTION_MODE must be HOMOLOGATION_SHADOW in homologation/staging"
        )
    if environment in {"production", "prod"} and (
        MODEL_EXECUTION_MODE != "CONTRACTUAL"
    ):
        errors.append("MODEL_EXECUTION_MODE must be CONTRACTUAL in production")
    if not DATABASE_URL.startswith(("postgresql://", "postgresql+psycopg://")):
        errors.append("DATABASE_URL must use the production PostgreSQL database")
    else:
        _validate_database_password(DATABASE_URL, errors)
    if ADMIN_API_KEY:
        errors.append("legacy ADMIN_API_KEY is forbidden; use ADMIN_CREDENTIALS_JSON")
    admin_credentials = _validate_credentials_json(
        ADMIN_CREDENTIALS_JSON,
        "ADMIN_CREDENTIALS_JSON",
        errors,
    )
    if (
        environment in {"homologation", "staging"}
        and admin_credentials is not None
        and len(admin_credentials) < 2
    ):
        errors.append(
            "ADMIN_CREDENTIALS_JSON must contain separate trainer and reviewer "
            "credentials in homologation/staging"
        )
    client_credentials = _validate_credentials_json(
        CLIENT_CREDENTIALS_JSON,
        "CLIENT_CREDENTIALS_JSON",
        errors,
    )
    _validate_unique_credentials(admin_credentials, client_credentials, errors)
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
) -> dict[str, str] | None:
    try:
        credentials = json.loads(value)
    except json.JSONDecodeError:
        errors.append(f"{name} must be valid JSON")
        return None
    if not isinstance(credentials, dict) or not credentials:
        errors.append(f"{name} must contain at least one credential")
        return None
    if any(
        not isinstance(actor, str)
        or not actor.strip()
        or not isinstance(key, str)
        or len(key) < 24
        for actor, key in credentials.items()
    ):
        errors.append(f"{name} contains an invalid or short credential")
        return None
    typed_credentials = {
        actor.strip(): key.strip() for actor, key in credentials.items()
    }
    if any(_is_placeholder_secret(key) for key in typed_credentials.values()):
        errors.append(f"{name} contains a known placeholder/default credential")
    if len(set(typed_credentials.values())) != len(typed_credentials):
        errors.append(f"{name} contains duplicated credential keys")
    return typed_credentials


def _validate_unique_credentials(
    admin_credentials: dict[str, str] | None,
    client_credentials: dict[str, str] | None,
    errors: list[str],
) -> None:
    if admin_credentials is None or client_credentials is None:
        return
    if set(admin_credentials.values()) & set(client_credentials.values()):
        errors.append(
            "ADMIN_CREDENTIALS_JSON and CLIENT_CREDENTIALS_JSON must use "
            "different credential keys"
        )


def _validate_database_password(database_url: str, errors: list[str]) -> None:
    try:
        parsed_url = make_url(database_url)
    except ArgumentError:
        errors.append("DATABASE_URL must be a valid PostgreSQL URL")
        return

    password = parsed_url.password or ""
    if _is_weak_database_password(
        password,
        username=parsed_url.username,
        database=parsed_url.database,
    ):
        errors.append(
            "DATABASE_URL must contain a strong, non-default database password "
            "(16+ characters and 3 classes, or 32+ characters and 2 classes)"
        )


def _is_weak_database_password(
    password: str,
    *,
    username: str | None,
    database: str | None,
) -> bool:
    if len(password) < 16 or _is_placeholder_secret(password):
        return True
    normalized_password = password.casefold()
    if normalized_password in {
        (username or "").strip().casefold(),
        (database or "").strip().casefold(),
    }:
        return True
    character_classes = sum(
        bool(re.search(pattern, password))
        for pattern in (r"[a-z]", r"[A-Z]", r"\d", r"[^A-Za-z0-9]")
    )
    return not (
        (len(password) >= 16 and character_classes >= 3)
        or (len(password) >= 32 and character_classes >= 2)
    )


def _is_placeholder_secret(secret: str) -> bool:
    normalized = secret.strip().casefold()
    return (
        not normalized
        or normalized in _PLACEHOLDER_SECRETS
        or normalized.startswith(_PLACEHOLDER_PREFIXES)
        or "at_least_24_random_characters" in normalized
        or normalized.startswith(("${", "<"))
    )
