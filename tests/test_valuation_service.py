from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.domain.exceptions import (
    InvalidOrderStatusTransitionError,
)
from app.infrastructure.database import SessionLocal
from app.repositories.order_status_history_sqlalchemy import (
    list_order_status_history,
)
from app.repositories.orders_sqlalchemy import (
    create_order,
    get_order_by_internal_id,
)
from app.repositories.valuations_sqlalchemy import (
    get_valuation_by_internal_order_id,
)
from app.schemas.order import OrderCreate, OrderStatus
from app.services.order_status_update import (
    update_order_status_with_history,
)
from app.services.valuation_service import (
    calculate_and_store_valuation,
)


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


def move_order_to_validating_input(
    internal_order_id: str,
) -> None:
    with SessionLocal() as session:
        updated_order = update_order_status_with_history(
            session=session,
            internal_order_id=internal_order_id,
            new_status=OrderStatus.VALIDATING_INPUT,
        )

    assert updated_order is not None
    assert updated_order.status == OrderStatus.VALIDATING_INPUT


def test_calculates_and_stores_valuation() -> None:
    internal_order_id = create_test_order("VALUATION-SERVICE-001")

    move_order_to_validating_input(internal_order_id)

    with SessionLocal() as session:
        valuation = calculate_and_store_valuation(
            session=session,
            internal_order_id=internal_order_id,
        )

    assert valuation is not None
    assert valuation.internal_order_id == internal_order_id
    assert valuation.method == "RULE_BASED_V1"
    assert valuation.estimated_value == Decimal("735000.00")
    assert valuation.minimum_value == Decimal("661500.00")
    assert valuation.maximum_value == Decimal("808500.00")
    assert valuation.price_per_m2 == Decimal("10500.00")
    assert valuation.reference_area_m2 == Decimal("70.00")
    assert valuation.confidence_score == Decimal("0.8000")

    with SessionLocal() as session:
        stored_order = get_order_by_internal_id(
            session=session,
            internal_order_id=internal_order_id,
        )

        stored_valuation = get_valuation_by_internal_order_id(
            session=session,
            internal_order_id=internal_order_id,
        )

        history = list_order_status_history(
            session=session,
            internal_order_id=internal_order_id,
        )

    assert stored_order is not None
    assert stored_order.status == OrderStatus.COMPLETED

    assert stored_valuation is not None
    assert stored_valuation.valuation_id == valuation.valuation_id

    assert len(history) == 2
    assert history[0].previous_status == "RECEIVED"
    assert history[0].new_status == "VALIDATING_INPUT"
    assert history[1].previous_status == "VALIDATING_INPUT"
    assert history[1].new_status == "COMPLETED"


def test_returns_existing_valuation_without_creating_duplicate() -> None:
    internal_order_id = create_test_order("VALUATION-SERVICE-002")

    move_order_to_validating_input(internal_order_id)

    with SessionLocal() as session:
        first_valuation = calculate_and_store_valuation(
            session=session,
            internal_order_id=internal_order_id,
        )

    with SessionLocal() as session:
        second_valuation = calculate_and_store_valuation(
            session=session,
            internal_order_id=internal_order_id,
        )

    assert first_valuation is not None
    assert second_valuation is not None
    assert second_valuation.valuation_id == (first_valuation.valuation_id)

    with SessionLocal() as session:
        history = list_order_status_history(
            session=session,
            internal_order_id=internal_order_id,
        )

    assert len(history) == 2


def test_returns_none_for_unknown_order() -> None:
    with SessionLocal() as session:
        valuation = calculate_and_store_valuation(
            session=session,
            internal_order_id=("00000000-0000-0000-0000-000000000000"),
        )

    assert valuation is None


def test_rejects_calculation_before_input_validation() -> None:
    internal_order_id = create_test_order("VALUATION-SERVICE-003")

    with SessionLocal() as session:
        with pytest.raises(InvalidOrderStatusTransitionError):
            calculate_and_store_valuation(
                session=session,
                internal_order_id=internal_order_id,
            )

    with SessionLocal() as session:
        stored_order = get_order_by_internal_id(
            session=session,
            internal_order_id=internal_order_id,
        )

        stored_valuation = get_valuation_by_internal_order_id(
            session=session,
            internal_order_id=internal_order_id,
        )

    assert stored_order is not None
    assert stored_order.status == OrderStatus.RECEIVED
    assert stored_valuation is None


def test_rolls_back_when_order_update_returns_none() -> None:
    internal_order_id = create_test_order("VALUATION-SERVICE-004")

    move_order_to_validating_input(internal_order_id)

    with SessionLocal() as session:
        with (
            patch(
                "app.services.valuation_service.update_order_status",
                return_value=None,
            ),
            patch.object(
                session,
                "rollback",
                wraps=session.rollback,
            ) as rollback_mock,
        ):
            valuation = calculate_and_store_valuation(
                session=session,
                internal_order_id=internal_order_id,
            )

    assert valuation is None
    rollback_mock.assert_called_once()

    with SessionLocal() as session:
        stored_order = get_order_by_internal_id(
            session=session,
            internal_order_id=internal_order_id,
        )

        stored_valuation = get_valuation_by_internal_order_id(
            session=session,
            internal_order_id=internal_order_id,
        )

    assert stored_order is not None
    assert stored_order.status == OrderStatus.VALIDATING_INPUT
    assert stored_valuation is None


def test_rolls_back_when_history_creation_fails() -> None:
    internal_order_id = create_test_order("VALUATION-SERVICE-005")

    move_order_to_validating_input(internal_order_id)

    with SessionLocal() as session:
        with (
            patch(
                "app.services.valuation_service.create_order_status_history",
                side_effect=RuntimeError("Falha ao registrar histórico."),
            ),
            patch.object(
                session,
                "rollback",
                wraps=session.rollback,
            ) as rollback_mock,
            pytest.raises(
                RuntimeError,
                match="Falha ao registrar histórico",
            ),
        ):
            calculate_and_store_valuation(
                session=session,
                internal_order_id=internal_order_id,
            )

    rollback_mock.assert_called_once()

    with SessionLocal() as session:
        stored_order = get_order_by_internal_id(
            session=session,
            internal_order_id=internal_order_id,
        )

        stored_valuation = get_valuation_by_internal_order_id(
            session=session,
            internal_order_id=internal_order_id,
        )

        history = list_order_status_history(
            session=session,
            internal_order_id=internal_order_id,
        )

    assert stored_order is not None
    assert stored_order.status == OrderStatus.VALIDATING_INPUT
    assert stored_valuation is None

    assert len(history) == 1
    assert history[0].previous_status == "RECEIVED"
    assert history[0].new_status == "VALIDATING_INPUT"
