from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_returns_standard_validation_error() -> None:
    request_id = "validation-error-test-001"

    response = client.get(
        "/orders/identificador-invalido",
        headers={
            "X-Request-ID": request_id,
        },
    )

    assert response.status_code == 422
    assert response.headers["X-Request-ID"] == request_id

    detail = response.json()["detail"]

    assert detail["code"] == "VALIDATION_ERROR"
    assert detail["message"] == (
        "Os dados enviados são inválidos."
    )
    assert detail["request_id"] == request_id
    assert len(detail["errors"]) >= 1

    first_error = detail["errors"][0]

    assert first_error["type"]
    assert first_error["message"]
    assert first_error["location"]


def test_validation_error_for_invalid_status() -> None:
    response = client.get(
        "/orders",
        params={
            "order_status": "STATUS_INEXISTENTE",
        },
    )

    assert response.status_code == 422

    detail = response.json()["detail"]

    assert detail["code"] == "VALIDATION_ERROR"
    assert detail["errors"]


def test_validation_error_for_missing_required_field() -> None:
    response = client.post(
        "/orders",
        json={
            "external_order_id": "INVALID-PAYLOAD-001",
        },
    )

    assert response.status_code == 422

    detail = response.json()["detail"]

    assert detail["code"] == "VALIDATION_ERROR"

    locations = [
        error["location"]
        for error in detail["errors"]
    ]

    assert ["body", "property"] in locations
