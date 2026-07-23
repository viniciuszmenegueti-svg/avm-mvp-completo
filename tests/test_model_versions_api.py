from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_lists_active_model_versions() -> None:
    response = client.get("/models")

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 1
    assert len(body["items"]) == 1


def test_returns_rule_based_v1_model_metadata() -> None:
    response = client.get("/models")

    assert response.status_code == 200

    model = response.json()["items"][0]

    assert model["method"] == "RULE_BASED_V1"
    assert model["version"] == "1.0.0"
    assert model["status"] == "ACTIVE"
    assert model["is_default"] is True
    assert model["description"]


def test_models_endpoint_is_available_in_openapi() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/models" in response.json()["paths"]
