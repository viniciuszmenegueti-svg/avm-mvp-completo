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
