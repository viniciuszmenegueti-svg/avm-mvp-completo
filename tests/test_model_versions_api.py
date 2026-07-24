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


def test_gets_registered_model_by_method() -> None:
    response = client.get("/models/RULE_BASED_V1")

    assert response.status_code == 200

    model = response.json()

    assert model["method"] == "RULE_BASED_V1"
    assert model["version"] == "1.0.0"
    assert model["status"] == "ACTIVE"
    assert model["is_default"] is True
    assert model["description"]


def test_returns_not_found_for_unknown_model() -> None:
    response = client.get("/models/UNKNOWN_MODEL")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Modelo AVM não encontrado.",
    }


def test_models_endpoints_are_available_in_openapi() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert "/models" in paths
    assert "/models/{method}" in paths
