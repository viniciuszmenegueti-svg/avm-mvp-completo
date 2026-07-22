from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.infrastructure.database import SessionLocal
from app.repositories.orders_sqlalchemy import create_order
from app.repositories.valuations_sqlalchemy import (
    create_valuation,
    get_valuation_by_internal_order_id,
)
from app.schemas.order import OrderCreate
from app.schemas.valuation import ValuationMethod


def order_payload(
    external_order_id: str,
) -> dict[str, object]:
    return {
        "external_order_id": external_order_id,
        "property": {
            "property_type": "APARTMENT",
            "state": "SP",
            "city": "São Paulo",
            "city_ibge_code": "3550308",
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


def create_test_order(
    external_order_id: str,
) -> str:
    internal_order_id = str(uuid4())

    order = OrderCreate.model_validate(order_payload(external_order_id))

    with SessionLocal() as session:
        create_order(
            session=session,
            order=order,
            internal_order_id=internal_order_id,
            received_at=datetime.now(timezone.utc),
        )

    return internal_order_id


def test_creates_and_reads_valuation() -> None:
    internal_order_id = create_test_order("VALUATION-REPOSITORY-001")
    valuation_id = str(uuid4())
    calculated_at = datetime.now(timezone.utc)

    with SessionLocal() as session:
        created_valuation = create_valuation(
            session=session,
            valuation_id=valuation_id,
            internal_order_id=internal_order_id,
            method=ValuationMethod.RULE_BASED_V1,
            estimated_value=Decimal("525000.00"),
            minimum_value=Decimal("472500.00"),
            maximum_value=Decimal("577500.00"),
            price_per_m2=Decimal("7500.00"),
            reference_area_m2=Decimal("70.00"),
            confidence_score=Decimal("0.7500"),
            calculated_at=calculated_at,
        )

    assert created_valuation.valuation_id == valuation_id
    assert created_valuation.internal_order_id == internal_order_id
    assert created_valuation.method == ValuationMethod.RULE_BASED_V1
    assert created_valuation.estimated_value == Decimal("525000.00")
    assert created_valuation.minimum_value == Decimal("472500.00")
    assert created_valuation.maximum_value == Decimal("577500.00")
    assert created_valuation.price_per_m2 == Decimal("7500.00")
    assert created_valuation.reference_area_m2 == Decimal("70.00")
    assert created_valuation.confidence_score == Decimal("0.7500")

    with SessionLocal() as session:
        stored_valuation = get_valuation_by_internal_order_id(
            session=session,
            internal_order_id=internal_order_id,
        )

    assert stored_valuation is not None
    assert stored_valuation.valuation_id == valuation_id
    assert stored_valuation.internal_order_id == internal_order_id
    assert stored_valuation.method == ValuationMethod.RULE_BASED_V1
    assert stored_valuation.estimated_value == Decimal("525000.00")
    assert stored_valuation.minimum_value == Decimal("472500.00")
    assert stored_valuation.maximum_value == Decimal("577500.00")
    assert stored_valuation.price_per_m2 == Decimal("7500.00")
    assert stored_valuation.reference_area_m2 == Decimal("70.00")
    assert stored_valuation.confidence_score == Decimal("0.7500")


def test_returns_none_for_unknown_order() -> None:
    with SessionLocal() as session:
        valuation = get_valuation_by_internal_order_id(
            session=session,
            internal_order_id=("00000000-0000-0000-0000-000000000000"),
        )

    assert valuation is None
