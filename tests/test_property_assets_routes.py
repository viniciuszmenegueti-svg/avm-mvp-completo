from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.property_asset import PropertyAssetResponse


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


@pytest.mark.parametrize(
    ("property_type", "areas", "invalid_patch", "preserved_field"),
    [
        (
            "APARTMENT",
            {
                "private_area_m2": "72.50",
                "built_area_m2": "85.00",
                "land_area_m2": None,
            },
            {"private_area_m2": None},
            "private_area_m2",
        ),
        (
            "APARTMENT",
            {
                "private_area_m2": "72.50",
                "built_area_m2": "85.00",
                "land_area_m2": None,
            },
            {"land_area_m2": "300.00"},
            "land_area_m2",
        ),
        (
            "HOUSE",
            {
                "private_area_m2": None,
                "built_area_m2": "120.00",
                "land_area_m2": "300.00",
            },
            {"built_area_m2": None},
            "built_area_m2",
        ),
        (
            "LAND",
            {
                "private_area_m2": None,
                "built_area_m2": None,
                "land_area_m2": "500.00",
            },
            {"land_area_m2": None},
            "land_area_m2",
        ),
    ],
)
def test_rejects_patch_that_would_break_complete_area_invariants(
    property_type: str,
    areas: dict[str, str | None],
    invalid_patch: dict[str, str | None],
    preserved_field: str,
) -> None:
    payload = valid_property_asset_payload()
    payload.update({"property_type": property_type, **areas})
    created = client.post("/property-assets", json=payload)
    assert created.status_code == 201
    property_asset_id = created.json()["property_asset_id"]
    original_value = created.json()[preserved_field]

    response = client.patch(
        f"/property-assets/{property_asset_id}",
        json=invalid_patch,
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_PROPERTY_ASSET_UPDATE"
    persisted = client.get(f"/property-assets/{property_asset_id}")
    assert persisted.status_code == 200
    assert persisted.json()[preserved_field] == original_value


def test_rolls_back_patch_when_response_validation_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = client.post("/property-assets", json=valid_property_asset_payload())
    assert created.status_code == 201
    property_asset_id = created.json()["property_asset_id"]

    def fail_response_validation(
        cls: type[PropertyAssetResponse], value: object
    ) -> None:
        del cls, value
        raise RuntimeError("simulated response validation failure")

    with monkeypatch.context() as context:
        context.setattr(
            PropertyAssetResponse,
            "model_validate",
            classmethod(fail_response_validation),
        )
        with pytest.raises(RuntimeError, match="simulated response validation failure"):
            client.patch(
                f"/property-assets/{property_asset_id}",
                json={"neighborhood": "Bairro que não deve persistir"},
            )

    persisted = client.get(f"/property-assets/{property_asset_id}")
    assert persisted.status_code == 200
    assert persisted.json()["neighborhood"] == "Centro"
