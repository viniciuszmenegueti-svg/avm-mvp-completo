import pytest

from app.core import production_readiness


def _set_safe_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(production_readiness, "APP_ENV", "production")
    monkeypatch.setattr(production_readiness, "APP_DEBUG", False)
    monkeypatch.setattr(production_readiness, "ALLOW_SYNTHETIC_PRICING", False)
    monkeypatch.setattr(
        production_readiness,
        "DATABASE_URL",
        "postgresql+psycopg://user:password@database/avm",
    )
    monkeypatch.setattr(production_readiness, "ADMIN_API_KEY", "")
    monkeypatch.setattr(
        production_readiness,
        "ADMIN_CREDENTIALS_JSON",
        '{"admin":"012345678901234567890123"}',
    )
    monkeypatch.setattr(
        production_readiness,
        "CLIENT_CREDENTIALS_JSON",
        '{"caixa":"012345678901234567890123"}',
    )


def test_accepts_safe_production_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_safe_production(monkeypatch)

    assert production_readiness.production_configuration_errors() == []
    production_readiness.assert_safe_production_configuration()


def test_rejects_synthetic_pricing_and_sqlite_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_safe_production(monkeypatch)
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
    _set_safe_production(monkeypatch)
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
    _set_safe_production(monkeypatch)
    monkeypatch.setattr(production_readiness, "APP_ENV", environment)

    assert production_readiness.production_configuration_errors() == []

    monkeypatch.setattr(production_readiness, "ALLOW_SYNTHETIC_PRICING", True)

    assert (
        "ALLOW_SYNTHETIC_PRICING must be false"
        in production_readiness.production_configuration_errors()
    )


def test_rejects_non_postgresql_database_in_secure_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_safe_production(monkeypatch)
    monkeypatch.setattr(
        production_readiness,
        "DATABASE_URL",
        "mysql://user:password@database/avm",
    )

    assert (
        "DATABASE_URL must use the production PostgreSQL database"
        in production_readiness.production_configuration_errors()
    )
