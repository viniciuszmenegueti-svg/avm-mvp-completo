from fastapi.testclient import TestClient

from app.main import app


client = TestClient(
    app,
    raise_server_exceptions=False,
)


def assert_security_headers(response) -> None:
    assert response.headers["X-Content-Type-Options"] == "nosniff"

    assert response.headers["X-Frame-Options"] == "DENY"

    assert response.headers["Referrer-Policy"] == "no-referrer"

    assert response.headers["Cache-Control"] == "no-store"


def test_adds_security_headers_to_success_response() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert_security_headers(response)


def test_adds_security_headers_to_not_found_response() -> None:
    response = client.get("/rota-inexistente")

    assert response.status_code == 404
    assert_security_headers(response)


def test_adds_security_headers_to_validation_error() -> None:
    response = client.get("/orders/identificador-invalido")

    assert response.status_code == 422
    assert_security_headers(response)
