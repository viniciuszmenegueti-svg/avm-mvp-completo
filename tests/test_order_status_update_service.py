from datetime import datetime, timezone
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
from app.schemas.order import (
    OrderCreate,
    OrderStatus,
)
from app.services.order_status_update import (
    update_order_status_with_history,
)


def order_payload(
    external_order_id: str,
) -> dict:
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

    order = OrderCreate.model_validate(
        order_payload(external_order_id)
    )

    with SessionLocal() as session:
        create_order(
            session=session,
            order=order,
            internal_order_id=internal_order_id,
            received_at=datetime.now(timezone.utc),
        )

    return internal_order_id


def test_updates_status_and_creates_history() -> None:
    internal_order_id = create_test_order(
        "STATUS-SERVICE-001"
    )

    with SessionLocal() as session:
        updated_order = update_order_status_with_history(
            session=session,
            internal_order_id=internal_order_id,
            new_status=OrderStatus.VALIDATING_INPUT,
        )

    assert updated_order is not None
    assert updated_order.status == (
        OrderStatus.VALIDATING_INPUT
    )

    with SessionLocal() as session:
        stored_order = get_order_by_internal_id(
            session=session,
            internal_order_id=internal_order_id,
        )

        history = list_order_status_history(
            session=session,
            internal_order_id=internal_order_id,
        )

    assert stored_order is not None
    assert stored_order.status == (
        OrderStatus.VALIDATING_INPUT
    )

    assert len(history) == 1
    assert history[0].previous_status == "RECEIVED"
    assert history[0].new_status == "VALIDATING_INPUT"


def test_returns_none_for_unknown_order() -> None:
    with SessionLocal() as session:
        updated_order = update_order_status_with_history(
            session=session,
            internal_order_id=(
                "00000000-0000-0000-0000-000000000000"
            ),
            new_status=OrderStatus.VALIDATING_INPUT,
        )

    assert updated_order is None


def test_rejects_invalid_transition_without_history() -> None:
    internal_order_id = create_test_order(
        "STATUS-SERVICE-002"
    )

    with SessionLocal() as session:
        with pytest.raises(
            InvalidOrderStatusTransitionError
        ):
            update_order_status_with_history(
                session=session,
                internal_order_id=internal_order_id,
                new_status=OrderStatus.COMPLETED,
            )

    with SessionLocal() as session:
        stored_order = get_order_by_internal_id(
            session=session,
            internal_order_id=internal_order_id,
        )

        history = list_order_status_history(
            session=session,
            internal_order_id=internal_order_id,
        )

    assert stored_order is not None
    assert stored_order.status == OrderStatus.RECEIVED
    assert history == []
