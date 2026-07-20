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
        "database": "ok",
    }


def test_root_endpoint() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == (
        "AVM Imóveis API em execução"
    )


def test_health_returns_503_when_database_is_unavailable(
    monkeypatch,
) -> None:
    from sqlalchemy.exc import OperationalError

    from app.api.routes import health as health_route

    class FailingSession:
        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ) -> None:
            return None

        def execute(self, statement):
            raise OperationalError(
                statement="SELECT 1",
                params={},
                orig=RuntimeError(
                    "Falha simulada de conexão"
                ),
            )

    monkeypatch.setattr(
        health_route,
        "SessionLocal",
        FailingSession,
    )

    response = client.get("/health")

    assert response.status_code == 503

    assert response.json()["detail"] == {
        "code": "DATABASE_UNAVAILABLE",
        "message": (
            "A API está em execução, mas o banco "
            "de dados não está disponível."
        ),
    }
