import pytest
from pydantic import ValidationError

from app.schemas.property import PropertyInput


def base_property_data() -> dict[str, object]:
    return {
        "state": "ES",
        "city": "Vitória",
        "city_ibge_code": "3205309",
        "postal_code": "29060-000",
        "neighborhood": "Jardim da Penha",
        "street": "Rua Exemplo",
        "number": "100",
    }


def test_valid_apartment() -> None:
    data = base_property_data()
    data.update(
        {
            "property_type": "APARTMENT",
            "private_area_m2": 72.5,
        }
    )

    property_data = PropertyInput(**data)

    assert property_data.private_area_m2 == 72.5
    assert property_data.land_area_m2 is None


def test_apartment_without_private_area_is_invalid() -> None:
    data = base_property_data()
    data.update(
        {
            "property_type": "APARTMENT",
        }
    )

    with pytest.raises(
        ValidationError,
        match="Apartamento deve possuir private_area_m2",
    ):
        PropertyInput(**data)


def test_apartment_with_land_area_is_invalid() -> None:
    data = base_property_data()
    data.update(
        {
            "property_type": "APARTMENT",
            "private_area_m2": 72.5,
            "land_area_m2": 300,
        }
    )

    with pytest.raises(
        ValidationError,
        match="Apartamento não deve possuir land_area_m2",
    ):
        PropertyInput(**data)


def test_valid_house() -> None:
    data = base_property_data()
    data.update(
        {
            "property_type": "HOUSE",
            "built_area_m2": 120,
            "land_area_m2": 250,
        }
    )

    property_data = PropertyInput(**data)

    assert property_data.built_area_m2 == 120
    assert property_data.land_area_m2 == 250


def test_house_without_built_area_is_invalid() -> None:
    data = base_property_data()
    data.update(
        {
            "property_type": "HOUSE",
            "land_area_m2": 250,
        }
    )

    with pytest.raises(
        ValidationError,
        match="Casa deve possuir built_area_m2",
    ):
        PropertyInput(**data)


def test_house_without_land_area_is_invalid() -> None:
    data = base_property_data()
    data.update(
        {
            "property_type": "HOUSE",
            "built_area_m2": 120,
        }
    )

    with pytest.raises(
        ValidationError,
        match="Casa deve possuir land_area_m2",
    ):
        PropertyInput(**data)


def test_valid_land() -> None:
    data = base_property_data()
    data.update(
        {
            "property_type": "LAND",
            "land_area_m2": 400,
        }
    )

    property_data = PropertyInput(**data)

    assert property_data.land_area_m2 == 400
    assert property_data.built_area_m2 is None


def test_land_without_land_area_is_invalid() -> None:
    data = base_property_data()
    data.update(
        {
            "property_type": "LAND",
        }
    )

    with pytest.raises(
        ValidationError,
        match="Terreno deve possuir land_area_m2",
    ):
        PropertyInput(**data)


def test_land_with_private_area_is_invalid() -> None:
    data = base_property_data()
    data.update(
        {
            "property_type": "LAND",
            "land_area_m2": 400,
            "private_area_m2": 100,
        }
    )

    with pytest.raises(
        ValidationError,
        match="Terreno não deve possuir private_area_m2",
    ):
        PropertyInput(**data)


def test_land_with_built_area_is_invalid() -> None:
    data = base_property_data()
    data.update(
        {
            "property_type": "LAND",
            "land_area_m2": 400,
            "built_area_m2": 100,
        }
    )

    with pytest.raises(
        ValidationError,
        match="Terreno não deve possuir built_area_m2",
    ):
        PropertyInput(**data)
