from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.infrastructure.dependencies import get_database_session
from app.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "avm-api",
        "name": "AVM Imóveis API",
        "version": "0.2.0",
        "environment": "test",
        "database": "ok",
    }


def test_liveness_endpoint() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "avm-api",
        "name": "AVM Imóveis API",
        "version": "0.2.0",
        "environment": "test",
    }


def test_readiness_endpoint() -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "avm-api",
        "name": "AVM Imóveis API",
        "version": "0.2.0",
        "environment": "test",
        "database": "ok",
    }


def test_root_endpoint() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == ("AVM Imóveis API em execução")


def test_health_returns_503_when_database_is_unavailable() -> None:
    class FailingSession:
        def execute(self, statement) -> None:
            raise OperationalError(
                statement="SELECT 1",
                params={},
                orig=RuntimeError("Falha simulada de conexão"),
            )

    def override_database_session() -> Generator[
        Session,
        None,
        None,
    ]:
        yield FailingSession()

    app.dependency_overrides[get_database_session] = override_database_session

    try:
        health_response = client.get("/health")
        ready_response = client.get("/health/ready")
        live_response = client.get("/health/live")

    finally:
        app.dependency_overrides.clear()

    assert health_response.status_code == 503
    assert ready_response.status_code == 503

    assert health_response.json()["detail"] == {
        "code": "DATABASE_UNAVAILABLE",
        "message": (
            "A API está em execução, mas o banco de dados não está disponível."
        ),
    }

    assert ready_response.json()["detail"]["code"] == ("DATABASE_UNAVAILABLE")

    assert live_response.status_code == 200
    assert live_response.json()["status"] == "ok"
