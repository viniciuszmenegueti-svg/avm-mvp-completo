import logging

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_logs_successful_http_request(
    caplog,
) -> None:
    with caplog.at_level(
        logging.INFO,
        logger="app.http",
    ):
        response = client.get(
            "/",
            headers={
                "X-Request-ID": "http-log-test-001",
            },
        )

    assert response.status_code == 200

    messages = [
        record.getMessage() for record in caplog.records if record.name == "app.http"
    ]

    assert any(
        "method=GET" in message
        and "path=/" in message
        and "status_code=200" in message
        and "duration_ms=" in message
        for message in messages
    )


def test_logs_not_found_response(
    caplog,
) -> None:
    with caplog.at_level(
        logging.INFO,
        logger="app.http",
    ):
        response = client.get("/rota-inexistente")

    assert response.status_code == 404

    messages = [
        record.getMessage() for record in caplog.records if record.name == "app.http"
    ]

    assert any(
        "method=GET" in message
        and "path=/rota-inexistente" in message
        and "status_code=404" in message
        for message in messages
    )
