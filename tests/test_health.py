from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "avm-api",
        "version": "0.1.0",
    }


def test_root_endpoint() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == (
        "AVM Imóveis API em execução"
    )
