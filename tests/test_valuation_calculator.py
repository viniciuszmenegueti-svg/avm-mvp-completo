from decimal import Decimal

import pytest

from app.schemas.property import (
    PropertyInput,
    PropertyType,
)
from engine.exceptions import (
    InvalidPricePerSquareMeterError,
    ReferenceAreaNotFoundError,
    ValuationCalculationError,
)
from engine.models.rule_based_v1 import (
    calculate_confidence_score,
    calculate_valuation,
    get_reference_area,
)


def apartment_property() -> PropertyInput:
    return PropertyInput(
        property_type=PropertyType.APARTMENT,
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
        property_type=PropertyType.HOUSE,
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
        property_type=PropertyType.LAND,
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
    calculation = calculate_valuation(
        property_data=apartment_property(),
        price_per_m2=Decimal("10500.00"),
    )

    assert calculation.method == "RULE_BASED_V1"
    assert calculation.reference_area_m2 == Decimal("70.00")
    assert calculation.price_per_m2 == Decimal("10500.00")
    assert calculation.estimated_value == Decimal("735000.00")
    assert calculation.minimum_value == Decimal("661500.00")
    assert calculation.maximum_value == Decimal("808500.00")
    assert calculation.confidence_score == Decimal("0.8000")


def test_uses_built_area_for_house() -> None:
    assert get_reference_area(house_property()) == Decimal("120.00")


def test_uses_land_area_for_land() -> None:
    assert get_reference_area(land_property()) == Decimal("400.00")


def test_confidence_score_uses_completed_optional_fields() -> None:
    assert calculate_confidence_score(land_property()) == Decimal("0.6000")


def test_rejects_non_positive_price_per_m2() -> None:
    price_per_m2 = Decimal("0.00")

    with pytest.raises(
        InvalidPricePerSquareMeterError,
        match=("O preço por metro quadrado deve ser maior que zero"),
    ) as exception_info:
        calculate_valuation(
            property_data=apartment_property(),
            price_per_m2=price_per_m2,
        )

    assert exception_info.value.price_per_m2 == price_per_m2
    assert isinstance(
        exception_info.value,
        ValuationCalculationError,
    )
    assert isinstance(
        exception_info.value,
        ValueError,
    )


def test_rejects_property_without_reference_area() -> None:
    property_data = apartment_property()
    property_data.private_area_m2 = None

    with pytest.raises(
        ReferenceAreaNotFoundError,
        match=("Não foi possível determinar a área de referência do imóvel"),
    ) as exception_info:
        get_reference_area(property_data)

    assert exception_info.value.property_type == PropertyType.APARTMENT
    assert isinstance(
        exception_info.value,
        ValuationCalculationError,
    )
    assert isinstance(
        exception_info.value,
        ValueError,
    )
