from pathlib import Path

import pytest

from app.schemas.property import PropertyInput
from app.services.shadow_valuation_service import (
    ShadowValuationServiceError,
    calculate_shadow_valuation,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_property(
    **overrides: object,
) -> PropertyInput:
    payload = {
        "property_type": "APARTMENT",
        "state": "RJ",
        "city": "Rio de Janeiro",
        "city_ibge_code": "3304557",
        "postal_code": "22000-000",
        "neighborhood": "Copacabana",
        "street": "Rua de Teste",
        "number": "100",
        "complement": "Apartamento 101",
        "private_area_m2": 100.0,
        "built_area_m2": 110.0,
        "land_area_m2": None,
        "bedrooms": 3,
        "bathrooms": 2,
        "parking_spaces": 1,
    }

    payload.update(overrides)

    return PropertyInput.model_validate(payload)


def test_calculates_shadow_valuation() -> None:
    property_data = build_property()

    result = calculate_shadow_valuation(
        property_data
    )

    assert result.model.name == "RJ_FIXED_SPLIT_V3"
    assert result.prediction.estimated_value_brl > 0
    assert result.prediction.confidence_lower_brl > 0
    assert (
        result.prediction.confidence_lower_brl
        < result.prediction.estimated_value_brl
        < result.prediction.confidence_upper_brl
    )
    assert result.prediction.execution_mode == "SHADOW"


def test_calculation_does_not_mutate_property() -> None:
    property_data = build_property()
    original = property_data.model_dump()

    calculate_shadow_valuation(property_data)

    assert property_data.model_dump() == original


def test_blocks_city_outside_model_domain() -> None:
    property_data = build_property(
        city_ibge_code="3550308",
        city="São Paulo",
        state="SP",
    )

    with pytest.raises(
        ShadowValuationServiceError,
        match="Cidade fora do domínio",
    ):
        calculate_shadow_valuation(property_data)


def test_blocks_unsupported_neighborhood() -> None:
    property_data = build_property(
        neighborhood="Ipanema",
    )

    with pytest.raises(
        ShadowValuationServiceError,
        match="Bairro fora do domínio",
    ):
        calculate_shadow_valuation(property_data)


def test_blocks_missing_bedrooms() -> None:
    property_data = build_property(
        bedrooms=None,
    )

    with pytest.raises(
        ShadowValuationServiceError,
        match="bedrooms",
    ):
        calculate_shadow_valuation(property_data)
