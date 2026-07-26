from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def valid_property_asset_payload() -> dict[str, object]:
    return {
        "property_type": "APARTMENT",
        "city_ibge_code": "3550308",
        "postal_code": "01001-000",
        "neighborhood": "Centro",
        "street": "Praça da Sé",
        "number": "100",
        "private_area_m2": "72.50",
        "built_area_m2": "85.00",
        "land_area_m2": None,
        "bedrooms": 3,
        "bathrooms": 2,
        "parking_spaces": 1,
    }


def test_creates_property_asset() -> None:
    response = client.post(
        "/property-assets",
        json=valid_property_asset_payload(),
    )

    assert response.status_code == 201

    property_asset = response.json()

    assert property_asset["property_asset_id"]
    assert property_asset["property_type"] == "APARTMENT"
    assert property_asset["city_ibge_code"] == "3550308"
    assert property_asset["postal_code"] == "01001-000"
    assert property_asset["private_area_m2"] == "72.50"
    assert property_asset["created_at"] is not None
    assert property_asset["updated_at"] is not None


def test_gets_property_asset_by_id() -> None:
    create_response = client.post(
        "/property-assets",
        json=valid_property_asset_payload(),
    )

    assert create_response.status_code == 201

    created_property_asset = create_response.json()
    property_asset_id = created_property_asset["property_asset_id"]

    response = client.get(f"/property-assets/{property_asset_id}")

    assert response.status_code == 200
    assert response.json() == created_property_asset


def test_returns_not_found_for_unknown_property_asset() -> None:
    property_asset_id = str(uuid4())

    response = client.get(f"/property-assets/{property_asset_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "PROPERTY_ASSET_NOT_FOUND",
        "message": "Imóvel não encontrado.",
        "property_asset_id": property_asset_id,
    }


def test_rejects_invalid_property_asset_id() -> None:
    response = client.get("/property-assets/invalid-property-asset-id")

    assert response.status_code == 422


def test_rejects_unknown_city() -> None:
    payload = valid_property_asset_payload()
    payload["city_ibge_code"] = "9999999"

    response = client.post(
        "/property-assets",
        json=payload,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "UNSUPPORTED_CITY",
        "message": ("A cidade informada não está habilitada para cadastro de imóveis."),
        "city_ibge_code": "9999999",
    }


def test_rejects_invalid_property_type() -> None:
    payload = valid_property_asset_payload()
    payload["property_type"] = "COMMERCIAL"

    response = client.post(
        "/property-assets",
        json=payload,
    )

    assert response.status_code == 422


def test_rejects_apartment_without_private_area() -> None:
    payload = valid_property_asset_payload()
    payload["private_area_m2"] = None

    response = client.post(
        "/property-assets",
        json=payload,
    )

    assert response.status_code == 422


def test_preserves_decimal_area_values() -> None:
    payload = valid_property_asset_payload()
    payload["private_area_m2"] = str(Decimal("72.55"))
    payload["built_area_m2"] = str(Decimal("85.75"))

    response = client.post(
        "/property-assets",
        json=payload,
    )

    assert response.status_code == 201

    property_asset = response.json()

    assert property_asset["private_area_m2"] == "72.55"
    assert property_asset["built_area_m2"] == "85.75"
