from fastapi.testclient import TestClient

from app.api.routes import orders
from app.main import app


client = TestClient(app)


def payload() -> dict[str, object]:
    return {
        "external_order_id": "SECURE-LOCATION-001",
        "property": {
            "property_type": "APARTMENT",
            "state": "SP",
            "city": "São Paulo",
            "city_ibge_code": "3550308",
            "postal_code": "01001-000",
            "neighborhood": "Centro",
            "street": "Rua de Teste",
            "number": "100",
            "private_area_m2": 70,
            "built_area_m2": 80,
            "bedrooms": 2,
            "bathrooms": 2,
            "parking_spaces": 1,
        },
    }


def test_secure_environment_refuses_non_auditable_confirmed_location(
    monkeypatch,
) -> None:
    monkeypatch.setattr(orders, "APP_ENV", "homologation")

    response = client.post("/orders", json=payload())

    assert response.status_code == 201
    order = response.json()
    assert order["status"] == "REFUSED"
    refusal = client.get(f"/orders/{order['internal_order_id']}/refusal").json()
    assert refusal["reason_code"] == "TR_9_5_D"
    assert refusal["evidence"]["condition"] == "LOCATION_NOT_AUDITABLE"
    assert refusal["details"]["auditable_location_required"] is True


def test_secure_environment_accepts_complete_location(monkeypatch) -> None:
    monkeypatch.setattr(orders, "APP_ENV", "production")
    complete = payload()
    complete["external_order_id"] = "SECURE-LOCATION-002"
    complete["location_confirmation"] = {
        "is_confirmed": True,
        "confirmation_method": "DOCUMENT_VALIDATION",
        "evidence_reference": "MATRICULA-12345",
        "verified_by": "RESPONSAVEL-TECNICO",
        "latitude": -23.55052,
        "longitude": -46.633308,
        "accuracy_meters": 50,
    }

    response = client.post("/orders", json=complete)

    assert response.status_code == 201
    assert response.json()["status"] == "RECEIVED"


def test_asset_order_cannot_bypass_secure_location_requirement(monkeypatch) -> None:
    monkeypatch.setattr(orders, "APP_ENV", "homologation")
    asset_response = client.post(
        "/property-assets",
        json={
            "property_type": "APARTMENT",
            "city_ibge_code": "3550308",
            "postal_code": "01001-000",
            "neighborhood": "Centro",
            "street": "Rua de Teste",
            "number": "200",
            "private_area_m2": "70.00",
            "built_area_m2": "80.00",
            "bedrooms": 2,
            "bathrooms": 2,
            "parking_spaces": 1,
        },
    )
    assert asset_response.status_code == 201

    response = client.post(
        "/orders/from-property-asset",
        json={
            "external_order_id": "SECURE-ASSET-LOCATION-001",
            "property_asset_id": asset_response.json()["property_asset_id"],
        },
    )

    assert response.status_code == 201
    order = response.json()
    assert order["status"] == "REFUSED"
    refusal = client.get(f"/orders/{order['internal_order_id']}/refusal").json()
    assert refusal["reason_code"] == "TR_9_5_D"
    assert refusal["evidence"]["condition"] == "LOCATION_NOT_AUDITABLE"
