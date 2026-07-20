from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_generates_request_id() -> None:
    response = client.get("/")

    assert response.status_code == 200

    request_id = response.headers["X-Request-ID"]

    parsed_request_id = UUID(request_id)

    assert str(parsed_request_id) == request_id


def test_preserves_request_id_sent_by_client() -> None:
    request_id = "request-test-001"

    response = client.get(
        "/",
        headers={
            "X-Request-ID": request_id,
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id


def test_request_id_is_added_to_error_response() -> None:
    response = client.get("/rota-inexistente")

    assert response.status_code == 404
    assert response.headers["X-Request-ID"]
