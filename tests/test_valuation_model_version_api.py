from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def apartment_payload(
    external_order_id: str,
) -> dict[str, object]:
    return {
        "external_order_id": external_order_id,
        "property": {
            "property_type": "APARTMENT",
            "state": "SP",
            "city": "São Paulo",
            "city_ibge_code": "3550308",
            "postal_code": "01001-000",
            "neighborhood": "Centro",
            "street": "Rua de Teste",
            "number": "100",
            "complement": "Apartamento 10",
            "private_area_m2": 70,
            "built_area_m2": 80,
            "land_area_m2": None,
            "bedrooms": 2,
            "bathrooms": 2,
            "parking_spaces": 1,
        },
    }


def create_validated_order(
    external_order_id: str,
) -> str:
    create_response = client.post(
        "/orders",
        json=apartment_payload(external_order_id),
    )

    assert create_response.status_code == 201

    internal_order_id = create_response.json()["internal_order_id"]

    status_response = client.patch(
        f"/orders/{internal_order_id}/status",
        json={
            "status": "VALIDATING_INPUT",
        },
    )

    assert status_response.status_code == 200

    return internal_order_id


def test_valuation_creation_returns_model_version() -> None:
    internal_order_id = create_validated_order("VALUATION-MODEL-VERSION-API-001")

    response = client.post(f"/orders/{internal_order_id}/valuation")

    assert response.status_code == 201

    valuation = response.json()

    assert valuation["method"] == "RULE_BASED_V1"
    assert valuation["model_version"] == "1.0.0"


def test_valuation_query_returns_persisted_model_version() -> None:
    internal_order_id = create_validated_order("VALUATION-MODEL-VERSION-API-002")

    create_response = client.post(f"/orders/{internal_order_id}/valuation")

    assert create_response.status_code == 201

    get_response = client.get(f"/orders/{internal_order_id}/valuation")

    assert get_response.status_code == 200

    valuation = get_response.json()

    assert valuation["valuation_id"] == (create_response.json()["valuation_id"])
    assert valuation["method"] == "RULE_BASED_V1"
    assert valuation["model_version"] == "1.0.0"


def test_model_version_is_required_in_openapi_schema() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200

    valuation_schema = response.json()["components"]["schemas"]["ValuationResponse"]

    assert "model_version" in valuation_schema["properties"]
    assert "model_version" in valuation_schema["required"]
