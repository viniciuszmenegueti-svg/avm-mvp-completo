from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.property_asset import (
    PropertyAssetCreate,
    PropertyAssetResponse,
)


def valid_property_asset_payload() -> dict[str, object]:
    return {
        "property_type": "APARTMENT",
        "city_ibge_code": "3205309",
        "postal_code": "29060000",
        "neighborhood": "Jardim da Penha",
        "street": "Av. Fernando Ferrari",
        "number": "100",
        "private_area_m2": Decimal("72.50"),
        "built_area_m2": Decimal("85.00"),
        "land_area_m2": None,
        "bedrooms": 3,
        "bathrooms": 2,
        "parking_spaces": 1,
    }


def test_accepts_valid_property_asset_create() -> None:
    asset = PropertyAssetCreate.model_validate(valid_property_asset_payload())

    assert asset.property_type == "APARTMENT"
    assert asset.city_ibge_code == "3205309"
    assert asset.private_area_m2 == Decimal("72.50")


def test_accepts_valid_property_asset_response() -> None:
    payload = {
        **valid_property_asset_payload(),
        "property_asset_id": ("00000000-0000-0000-0000-000000000001"),
        "created_at": "2026-07-24T10:00:00Z",
        "updated_at": "2026-07-24T10:00:00Z",
    }

    asset = PropertyAssetResponse.model_validate(payload)

    assert asset.property_asset_id
    assert asset.created_at is not None
    assert asset.updated_at is not None


def test_rejects_invalid_ibge_code_length() -> None:
    payload = valid_property_asset_payload()
    payload["city_ibge_code"] = "123"

    with pytest.raises(ValidationError):
        PropertyAssetCreate.model_validate(payload)


def test_rejects_missing_street() -> None:
    payload = valid_property_asset_payload()
    del payload["street"]

    with pytest.raises(ValidationError):
        PropertyAssetCreate.model_validate(payload)
