from decimal import Decimal

import pytest

from app.schemas.property import PropertyInput
from app.services.valuation_calculator import (
    calculate_confidence_score,
    calculate_valuation,
    get_base_price_per_m2,
    get_reference_area,
)


def apartment_property() -> PropertyInput:
    return PropertyInput(
        property_type="APARTMENT",
        state="SP",
        city="São Paulo",
        city_ibge_code="3550308",
        postal_code="01001-000",
        neighborhood="Centro",
        street="Rua de Teste",
        number="100",
        complement="Apartamento 10",
        private_area_m2=70,
        built_area_m2=80,
        bedrooms=2,
        bathrooms=2,
        parking_spaces=1,
    )


def house_property() -> PropertyInput:
    return PropertyInput(
        property_type="HOUSE",
        state="SP",
        city="São Paulo",
        city_ibge_code="3550308",
        postal_code="01001-000",
        neighborhood="Centro",
        street="Rua de Teste",
        number="100",
        built_area_m2=120,
        land_area_m2=250,
        bedrooms=3,
        bathrooms=2,
        parking_spaces=2,
    )


def land_property() -> PropertyInput:
    return PropertyInput(
        property_type="LAND",
        state="SP",
        city="São Paulo",
        city_ibge_code="3550308",
        postal_code="01001-000",
        neighborhood="Centro",
        street="Rua de Teste",
        number="100",
        land_area_m2=400,
    )


def test_calculates_apartment_valuation() -> None:
    calculation = calculate_valuation(apartment_property())

    assert calculation.method == "RULE_BASED_V1"
    assert calculation.reference_area_m2 == Decimal("70.00")
    assert calculation.price_per_m2 == Decimal("10500.00")
    assert calculation.estimated_value == Decimal("735000.00")
    assert calculation.minimum_value == Decimal("661500.00")
    assert calculation.maximum_value == Decimal("808500.00")
    assert calculation.confidence_score == Decimal("0.8000")


def test_uses_built_area_for_house() -> None:
    property_data = house_property()

    assert get_reference_area(property_data) == Decimal("120.00")

    assert get_base_price_per_m2(property_data) == Decimal("7800.00")


def test_uses_land_area_for_land() -> None:
    property_data = land_property()

    assert get_reference_area(property_data) == Decimal("400.00")

    assert get_base_price_per_m2(property_data) == Decimal("5200.00")


def test_confidence_score_uses_completed_optional_fields() -> None:
    property_data = land_property()

    assert calculate_confidence_score(property_data) == Decimal("0.6000")


def test_rejects_city_without_base_price() -> None:
    property_data = apartment_property()
    property_data.city_ibge_code = "3205309"

    with pytest.raises(
        ValueError,
        match="Não existe preço-base configurado para a cidade",
    ):
        get_base_price_per_m2(property_data)
