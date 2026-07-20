import logging

from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.main import app


error_test_router = APIRouter()


@error_test_router.get("/test-unexpected-error")
def raise_unexpected_error() -> None:
    raise RuntimeError("Erro interno utilizado somente no teste")


app.include_router(error_test_router)

client = TestClient(
    app,
    raise_server_exceptions=False,
)


def test_returns_standard_internal_error_response() -> None:
    request_id = "internal-error-test-001"

    response = client.get(
        "/test-unexpected-error",
        headers={
            "X-Request-ID": request_id,
        },
    )

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == request_id

    assert response.json() == {
        "detail": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": ("Ocorreu um erro interno inesperado."),
            "request_id": request_id,
        }
    }


def test_logs_unexpected_error(
    caplog,
) -> None:
    with caplog.at_level(
        logging.ERROR,
        logger="app.errors",
    ):
        response = client.get(
            "/test-unexpected-error",
            headers={
                "X-Request-ID": "internal-error-log-001",
            },
        )

    assert response.status_code == 500

    records = [record for record in caplog.records if record.name == "app.errors"]

    assert any(
        "unexpected_error" in record.getMessage()
        and "method=GET" in record.getMessage()
        and "path=/test-unexpected-error" in record.getMessage()
        and "error_type=RuntimeError" in record.getMessage()
        for record in records
    )
