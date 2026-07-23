from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_rejects_admin_operation_when_key_is_not_configured() -> None:
    with patch(
        "app.core.admin_auth.ADMIN_API_KEY",
        "",
    ):
        response = client.patch(
            "/cities/3550308/valuation-prices/APARTMENT",
            headers={
                "X-Admin-API-Key": "any-key",
            },
            json={
                "price_per_m2": "11000.00",
            },
        )

    assert response.status_code == 503

    assert response.json()["detail"] == {
        "code": "ADMIN_API_KEY_NOT_CONFIGURED",
        "message": (
            "A chave administrativa não está configurada no ambiente da aplicação."
        ),
    }


def test_rejects_admin_operation_when_actor_is_not_configured() -> None:
    with (
        patch(
            "app.core.admin_auth.ADMIN_API_KEY",
            "configured-key",
        ),
        patch(
            "app.core.admin_auth.ADMIN_ACTOR",
            "",
        ),
    ):
        response = client.patch(
            "/cities/3550308/valuation-prices/APARTMENT",
            headers={
                "X-Admin-API-Key": "configured-key",
            },
            json={
                "price_per_m2": "11000.00",
            },
        )

    assert response.status_code == 503

    assert response.json()["detail"] == {
        "code": "ADMIN_ACTOR_NOT_CONFIGURED",
        "message": (
            "O responsável administrativo não está "
            "configurado no ambiente da aplicação."
        ),
    }


def test_records_actor_configured_on_server() -> None:
    with (
        patch(
            "app.core.admin_auth.ADMIN_API_KEY",
            "configured-key",
        ),
        patch(
            "app.core.admin_auth.ADMIN_ACTOR",
            "server-admin",
        ),
    ):
        update_response = client.patch(
            "/cities/3550308/valuation-prices/APARTMENT",
            headers={
                "X-Admin-API-Key": "configured-key",
                "X-Admin-Actor": "spoofed-client-actor",
            },
            json={
                "price_per_m2": "11000.00",
            },
        )

    assert update_response.status_code == 200

    history_response = client.get("/cities/3550308/valuation-prices/APARTMENT/history")

    assert history_response.status_code == 200

    history = history_response.json()

    assert history["total"] == 1
    assert history["items"][0]["changed_by"] == "server-admin"
