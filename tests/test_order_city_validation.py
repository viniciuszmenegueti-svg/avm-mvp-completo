import pytest

from app.domain.exceptions import UnsupportedCityError
from app.infrastructure.database import SessionLocal
from app.schemas.order import OrderCreate
from app.services.order_validation import (
    validate_order_city,
)


def order_payload(
    city_ibge_code: str,
    city: str,
    state: str,
) -> dict:
    return {
        "external_order_id": "CITY-VALIDATION-001",
        "property": {
            "property_type": "APARTMENT",
            "state": state,
            "city": city,
            "city_ibge_code": city_ibge_code,
            "postal_code": "01001-000",
            "neighborhood": "Centro",
            "street": "Rua de Teste",
            "number": "100",
            "complement": "Apartamento 10",
            "private_area_m2": 70,
            "built_area_m2": 80,
            "land_area_m2": None,
            "bedrooms": 2,
            "bathrooms": 2,
            "parking_spaces": 1,
        },
    }


def test_accepts_active_city() -> None:
    order = OrderCreate.model_validate(
        order_payload(
            city_ibge_code="3550308",
            city="São Paulo",
            state="SP",
        )
    )

    with SessionLocal() as session:
        validate_order_city(
            session=session,
            order=order,
        )


def test_rejects_unsupported_city() -> None:
    order = OrderCreate.model_validate(
        order_payload(
            city_ibge_code="3205309",
            city="Vitória",
            state="ES",
        )
    )

    with SessionLocal() as session:
        with pytest.raises(
            UnsupportedCityError
        ) as error:
            validate_order_city(
                session=session,
                order=order,
            )

    assert error.value.city_ibge_code == "3205309"


def test_rejects_unknown_ibge_code() -> None:
    order = OrderCreate.model_validate(
        order_payload(
            city_ibge_code="9999999",
            city="Cidade Inexistente",
            state="SP",
        )
    )

    with SessionLocal() as session:
        with pytest.raises(
            UnsupportedCityError
        ):
            validate_order_city(
                session=session,
                order=order,
            )
