from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_endpoint() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "AVM Imóveis API em execução",
        "name": "AVM Imóveis API",
        "version": "0.3.0",
        "status": "running",
        "documentation": "/docs",
    }


def test_root_endpoint_security_headers() -> None:
    response = client.get("/")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_root_endpoint_returns_request_id() -> None:
    request_id = "test-root-request-id"

    response = client.get(
        "/",
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id
