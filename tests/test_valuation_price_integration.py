from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)

ADMIN_HEADERS = {
    "X-Admin-API-Key": "avm-test-admin-key",
}


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


def test_updated_price_changes_valuation_result() -> None:
    update_response = client.patch(
        "/cities/3550308/valuation-prices/APARTMENT",
        headers=ADMIN_HEADERS,
        json={
            "price_per_m2": "11000.00",
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["price_per_m2"] == "11000.00"

    create_order_response = client.post(
        "/orders",
        json=apartment_payload("VALUATION-PRICE-INTEGRATION-001"),
    )

    assert create_order_response.status_code == 201

    internal_order_id = create_order_response.json()["internal_order_id"]

    status_response = client.patch(
        f"/orders/{internal_order_id}/status",
        json={
            "status": "VALIDATING_INPUT",
        },
    )

    assert status_response.status_code == 200

    valuation_response = client.post(f"/orders/{internal_order_id}/valuation")

    assert valuation_response.status_code == 201

    valuation = valuation_response.json()

    assert valuation["price_per_m2"] == "11000.00"
    assert valuation["reference_area_m2"] == "70.00"
    assert valuation["estimated_value"] == "770000.00"
    assert valuation["minimum_value"] == "693000.00"
    assert valuation["maximum_value"] == "847000.00"

    history_response = client.get("/cities/3550308/valuation-prices/APARTMENT/history")

    assert history_response.status_code == 200

    history = history_response.json()

    assert history["total"] == 1
    assert history["items"][0]["changed_by"] == "avm-test-admin"
