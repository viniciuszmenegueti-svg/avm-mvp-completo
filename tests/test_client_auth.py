from fastapi import HTTPException
import pytest

from app.core import client_auth


def test_client_auth_is_optional_outside_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(client_auth, "APP_ENV", "test")
    monkeypatch.setattr(client_auth, "CLIENT_CREDENTIALS_JSON", "")

    assert client_auth.require_client_api_key() == "development-anonymous"


def test_client_auth_requires_key_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(client_auth, "APP_ENV", "production")
    monkeypatch.setattr(
        client_auth,
        "CLIENT_CREDENTIALS_JSON",
        '{"caixa":"012345678901234567890123"}',
    )

    with pytest.raises(HTTPException) as error:
        client_auth.require_client_api_key()

    assert error.value.status_code == 401


def test_client_auth_resolves_actor_with_constant_time_comparison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(client_auth, "APP_ENV", "production")
    monkeypatch.setattr(
        client_auth,
        "CLIENT_CREDENTIALS_JSON",
        '{"caixa":"012345678901234567890123"}',
    )

    assert client_auth.require_client_api_key("012345678901234567890123") == "caixa"
