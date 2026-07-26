from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.property import PropertyType
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

    assert asset.property_type == PropertyType.APARTMENT
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


def test_rejects_non_numeric_ibge_code() -> None:
    payload = valid_property_asset_payload()
    payload["city_ibge_code"] = "32A5309"

    with pytest.raises(ValidationError):
        PropertyAssetCreate.model_validate(payload)


def test_rejects_missing_street() -> None:
    payload = valid_property_asset_payload()
    del payload["street"]

    with pytest.raises(ValidationError):
        PropertyAssetCreate.model_validate(payload)


def test_rejects_invalid_property_type() -> None:
    payload = valid_property_asset_payload()
    payload["property_type"] = "COMMERCIAL"

    with pytest.raises(ValidationError):
        PropertyAssetCreate.model_validate(payload)


def test_rejects_negative_private_area() -> None:
    payload = valid_property_asset_payload()
    payload["private_area_m2"] = Decimal("-10.00")

    with pytest.raises(ValidationError):
        PropertyAssetCreate.model_validate(payload)


def test_rejects_apartment_without_private_area() -> None:
    payload = valid_property_asset_payload()
    payload["private_area_m2"] = None

    with pytest.raises(
        ValidationError,
        match="Apartamento deve possuir private_area_m2",
    ):
        PropertyAssetCreate.model_validate(payload)


def test_rejects_apartment_with_land_area() -> None:
    payload = valid_property_asset_payload()
    payload["land_area_m2"] = Decimal("300.00")

    with pytest.raises(
        ValidationError,
        match="Apartamento não deve possuir land_area_m2",
    ):
        PropertyAssetCreate.model_validate(payload)


def test_accepts_valid_house() -> None:
    payload = valid_property_asset_payload()
    payload.update(
        {
            "property_type": "HOUSE",
            "private_area_m2": None,
            "built_area_m2": Decimal("120.00"),
            "land_area_m2": Decimal("300.00"),
        }
    )

    asset = PropertyAssetCreate.model_validate(payload)

    assert asset.property_type == PropertyType.HOUSE
    assert asset.built_area_m2 == Decimal("120.00")
    assert asset.land_area_m2 == Decimal("300.00")


def test_rejects_house_without_built_area() -> None:
    payload = valid_property_asset_payload()
    payload.update(
        {
            "property_type": "HOUSE",
            "private_area_m2": None,
            "built_area_m2": None,
            "land_area_m2": Decimal("300.00"),
        }
    )

    with pytest.raises(
        ValidationError,
        match="Casa deve possuir built_area_m2",
    ):
        PropertyAssetCreate.model_validate(payload)


def test_rejects_house_without_land_area() -> None:
    payload = valid_property_asset_payload()
    payload.update(
        {
            "property_type": "HOUSE",
            "private_area_m2": None,
            "built_area_m2": Decimal("120.00"),
            "land_area_m2": None,
        }
    )

    with pytest.raises(
        ValidationError,
        match="Casa deve possuir land_area_m2",
    ):
        PropertyAssetCreate.model_validate(payload)


def test_accepts_valid_land() -> None:
    payload = valid_property_asset_payload()
    payload.update(
        {
            "property_type": "LAND",
            "private_area_m2": None,
            "built_area_m2": None,
            "land_area_m2": Decimal("500.00"),
            "bedrooms": None,
            "bathrooms": None,
            "parking_spaces": None,
        }
    )

    asset = PropertyAssetCreate.model_validate(payload)

    assert asset.property_type == PropertyType.LAND
    assert asset.land_area_m2 == Decimal("500.00")


def test_rejects_land_without_land_area() -> None:
    payload = valid_property_asset_payload()
    payload.update(
        {
            "property_type": "LAND",
            "private_area_m2": None,
            "built_area_m2": None,
            "land_area_m2": None,
        }
    )

    with pytest.raises(
        ValidationError,
        match="Terreno deve possuir land_area_m2",
    ):
        PropertyAssetCreate.model_validate(payload)


def test_rejects_land_with_private_area() -> None:
    payload = valid_property_asset_payload()
    payload.update(
        {
            "property_type": "LAND",
            "private_area_m2": Decimal("50.00"),
            "built_area_m2": None,
            "land_area_m2": Decimal("500.00"),
        }
    )

    with pytest.raises(
        ValidationError,
        match="Terreno não deve possuir private_area_m2",
    ):
        PropertyAssetCreate.model_validate(payload)


def test_rejects_land_with_built_area() -> None:
    payload = valid_property_asset_payload()
    payload.update(
        {
            "property_type": "LAND",
            "private_area_m2": None,
            "built_area_m2": Decimal("50.00"),
            "land_area_m2": Decimal("500.00"),
        }
    )

    with pytest.raises(
        ValidationError,
        match="Terreno não deve possuir built_area_m2",
    ):
        PropertyAssetCreate.model_validate(payload)


def test_rejects_negative_bedrooms() -> None:
    payload = valid_property_asset_payload()
    payload["bedrooms"] = -1

    with pytest.raises(ValidationError):
        PropertyAssetCreate.model_validate(payload)


def test_rejects_excessive_bathrooms() -> None:
    payload = valid_property_asset_payload()
    payload["bathrooms"] = 21

    with pytest.raises(ValidationError):
        PropertyAssetCreate.model_validate(payload)
