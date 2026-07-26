from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def asset_payload(number: str = "100") -> dict[str, object]:
    return {
        "property_type": "APARTMENT",
        "city_ibge_code": "3550308",
        "postal_code": "01001-000",
        "neighborhood": "Centro",
        "street": "Praça da Sé",
        "number": number,
        "complement": "Apartamento 10",
        "private_area_m2": "72.50",
        "built_area_m2": "85.00",
        "land_area_m2": None,
        "bedrooms": 3,
        "bathrooms": 2,
        "parking_spaces": 1,
    }


def create_asset(number: str = "100") -> dict[str, object]:
    response = client.post("/property-assets", json=asset_payload(number))
    assert response.status_code == 201
    return response.json()


def test_lists_filters_and_updates_property_assets() -> None:
    first = create_asset("100")
    create_asset("200")

    listing = client.get("/property-assets?city_ibge_code=3550308&limit=1")
    assert listing.status_code == 200
    assert listing.json()["total"] == 2
    assert len(listing.json()["items"]) == 1

    update = client.patch(
        f"/property-assets/{first['property_asset_id']}",
        json={"bedrooms": 4, "complement": "Apartamento 11"},
    )
    assert update.status_code == 200
    assert update.json()["bedrooms"] == 4
    assert update.json()["complement"] == "Apartamento 11"


def test_rejects_duplicate_property_asset() -> None:
    first = create_asset()
    duplicate = client.post("/property-assets", json=asset_payload())
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["property_asset_id"] == first["property_asset_id"]


def test_returns_not_found_when_updating_unknown_asset() -> None:
    response = client.patch(
        "/property-assets/00000000-0000-0000-0000-000000000099",
        json={"bedrooms": 2},
    )
    assert response.status_code == 404


def test_creates_order_from_property_asset_and_explains_valuation() -> None:
    asset = create_asset()
    order_response = client.post(
        "/orders/from-property-asset",
        json={
            "external_order_id": "ASSET-ORDER-001",
            "property_asset_id": asset["property_asset_id"],
        },
    )
    assert order_response.status_code == 201
    order = order_response.json()
    assert order["property"]["street"] == "Praça da Sé"

    status_response = client.patch(
        f"/orders/{order['internal_order_id']}/status",
        json={"status": "VALIDATING_INPUT"},
    )
    assert status_response.status_code == 200

    valuation_response = client.post(f"/orders/{order['internal_order_id']}/valuation")
    assert valuation_response.status_code == 201
    valuation = valuation_response.json()
    assert valuation["factors"]["base_price_per_m2"] == "10500.00"
    assert valuation["factors"]["reference_area_m2"] == "72.50"
    assert valuation["confidence_reasons"]


def test_rejects_unknown_property_asset_for_order() -> None:
    response = client.post(
        "/orders/from-property-asset",
        json={
            "external_order_id": "ASSET-ORDER-404",
            "property_asset_id": "00000000-0000-0000-0000-000000000099",
        },
    )
    assert response.status_code == 404


def test_rejects_duplicate_external_id_for_asset_order() -> None:
    asset = create_asset()
    payload = {
        "external_order_id": "ASSET-ORDER-DUP",
        "property_asset_id": asset["property_asset_id"],
    }
    assert client.post("/orders/from-property-asset", json=payload).status_code == 201
    assert client.post("/orders/from-property-asset", json=payload).status_code == 409


def test_admin_diagnostics() -> None:
    create_asset()
    response = client.get(
        "/admin/diagnostics",
        headers={"X-Admin-API-Key": "avm-test-admin-key"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["actor"] == "avm-test-admin"
    assert body["counts"]["property_assets"] == 1
    assert "RECEIVED" in body["orders_by_status"]
