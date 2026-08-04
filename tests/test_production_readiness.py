import pytest

from app.core import production_readiness


def _set_safe_homologation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(production_readiness, "APP_ENV", "homologation")
    monkeypatch.setattr(production_readiness, "APP_DEBUG", False)
    monkeypatch.setattr(production_readiness, "ALLOW_SYNTHETIC_PRICING", False)
    monkeypatch.setattr(
        production_readiness,
        "MODEL_EXECUTION_MODE",
        "HOMOLOGATION_SHADOW",
    )
    monkeypatch.setattr(
        production_readiness,
        "DATABASE_URL",
        "postgresql+psycopg://user:LongStrongDbPassword42!@database/avm",
    )
    monkeypatch.setattr(production_readiness, "ADMIN_API_KEY", "")
    monkeypatch.setattr(
        production_readiness,
        "ADMIN_CREDENTIALS_JSON",
        (
            '{"trainer":"adm-Z8p3R7v2N5x9Q4k6T1m8W0c",'
            '"reviewer":"rev-T6c1M9q4Y2w8K5n7P3x0H6s"}'
        ),
    )
    monkeypatch.setattr(
        production_readiness,
        "CLIENT_CREDENTIALS_JSON",
        '{"caixa":"cli-B4y7H2s9L5n1P8d3K6q0V2x"}',
    )


def test_accepts_safe_homologation_shadow_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_safe_homologation(monkeypatch)

    assert production_readiness.production_configuration_errors() == []
    production_readiness.assert_safe_production_configuration()


def test_rejects_synthetic_pricing_and_sqlite_in_secure_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_safe_homologation(monkeypatch)
    monkeypatch.setattr(production_readiness, "ALLOW_SYNTHETIC_PRICING", True)
    monkeypatch.setattr(production_readiness, "DATABASE_URL", "sqlite:///avm.db")

    errors = production_readiness.production_configuration_errors()

    assert "ALLOW_SYNTHETIC_PRICING must be false" in errors
    assert "DATABASE_URL must use the production PostgreSQL database" in errors
    with pytest.raises(production_readiness.UnsafeProductionConfiguration):
        production_readiness.assert_safe_production_configuration()


def test_rejects_unknown_environment_instead_of_failing_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_safe_homologation(monkeypatch)
    monkeypatch.setattr(production_readiness, "APP_ENV", "prodution")

    errors = production_readiness.production_configuration_errors()

    assert len(errors) == 1
    assert errors[0].startswith("APP_ENV must be one of:")
    with pytest.raises(production_readiness.UnsafeProductionConfiguration):
        production_readiness.assert_safe_production_configuration()


@pytest.mark.parametrize("environment", ["homologation", "staging"])
def test_secure_non_production_environments_use_production_guards(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_safe_homologation(monkeypatch)
    monkeypatch.setattr(production_readiness, "APP_ENV", environment)
    assert production_readiness.production_configuration_errors() == []

    monkeypatch.setattr(production_readiness, "ALLOW_SYNTHETIC_PRICING", True)

    assert (
        "ALLOW_SYNTHETIC_PRICING must be false"
        in production_readiness.production_configuration_errors()
    )


def test_rejects_execution_mode_incompatible_with_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_safe_homologation(monkeypatch)
    monkeypatch.setattr(production_readiness, "APP_ENV", "production")
    monkeypatch.setattr(production_readiness, "MODEL_EXECUTION_MODE", "DEMONSTRATION")

    assert (
        "MODEL_EXECUTION_MODE must be CONTRACTUAL in production"
        in production_readiness.production_configuration_errors()
    )

    monkeypatch.setattr(production_readiness, "MODEL_EXECUTION_MODE", "UNKNOWN")
    assert production_readiness.production_configuration_errors()[0].startswith(
        "MODEL_EXECUTION_MODE must be one of:"
    )


@pytest.mark.parametrize("environment", ["development", "homologation", "production"])
def test_contractual_mode_is_blocked_until_formal_external_gates(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    _set_safe_homologation(monkeypatch)
    monkeypatch.setattr(production_readiness, "APP_ENV", environment)
    monkeypatch.setattr(production_readiness, "MODEL_EXECUTION_MODE", "CONTRACTUAL")

    errors = production_readiness.production_configuration_errors()

    assert production_readiness.CONTRACTUAL_MODE_BLOCKED_ERROR in errors
    with pytest.raises(production_readiness.UnsafeProductionConfiguration):
        production_readiness.assert_safe_production_configuration()


def test_rejects_non_postgresql_database_in_secure_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_safe_homologation(monkeypatch)
    monkeypatch.setattr(
        production_readiness,
        "DATABASE_URL",
        "mysql://user:password@database/avm",
    )

    assert (
        "DATABASE_URL must use the production PostgreSQL database"
        in production_readiness.production_configuration_errors()
    )


@pytest.mark.parametrize(
    "secret",
    [
        "replace_with_at_least_24_random_characters",
        "change_this_admin_key_123456789",
        "<insert-a-secure-key-here>",
    ],
)
def test_rejects_known_credential_placeholders(
    monkeypatch: pytest.MonkeyPatch,
    secret: str,
) -> None:
    _set_safe_homologation(monkeypatch)
    monkeypatch.setattr(
        production_readiness,
        "ADMIN_CREDENTIALS_JSON",
        '{"admin":' + repr(secret).replace("'", '"') + "}",
    )

    assert (
        "ADMIN_CREDENTIALS_JSON contains a known placeholder/default credential"
        in production_readiness.production_configuration_errors()
    )


def test_rejects_duplicated_credentials_within_and_between_roles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_safe_homologation(monkeypatch)
    shared_key = "shared-Z8p3R7v2N5x9Q4k6T1m8W0c"
    monkeypatch.setattr(
        production_readiness,
        "ADMIN_CREDENTIALS_JSON",
        '{"admin-a":"' + shared_key + '","admin-b":"' + shared_key + '"}',
    )
    monkeypatch.setattr(
        production_readiness,
        "CLIENT_CREDENTIALS_JSON",
        '{"caixa":"' + shared_key + '"}',
    )

    errors = production_readiness.production_configuration_errors()

    assert "ADMIN_CREDENTIALS_JSON contains duplicated credential keys" in errors
    assert (
        "ADMIN_CREDENTIALS_JSON and CLIENT_CREDENTIALS_JSON must use different "
        "credential keys" in errors
    )


def test_requires_separate_trainer_and_reviewer_in_homologation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_safe_homologation(monkeypatch)
    monkeypatch.setattr(
        production_readiness,
        "ADMIN_CREDENTIALS_JSON",
        '{"trainer":"adm-Z8p3R7v2N5x9Q4k6T1m8W0c"}',
    )

    assert any(
        error.startswith("ADMIN_CREDENTIALS_JSON must contain separate")
        for error in production_readiness.production_configuration_errors()
    )


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql+psycopg://user:change_me@database/avm",
        "postgresql+psycopg://user:password@database/avm",
        "postgresql+psycopg://user:alllowercasepassword@database/avm",
    ],
)
def test_rejects_weak_or_default_database_passwords(
    monkeypatch: pytest.MonkeyPatch,
    database_url: str,
) -> None:
    _set_safe_homologation(monkeypatch)
    monkeypatch.setattr(production_readiness, "DATABASE_URL", database_url)

    assert any(
        error.startswith("DATABASE_URL must contain a strong, non-default")
        for error in production_readiness.production_configuration_errors()
    )
