from datetime import datetime, timezone
from uuid import uuid4

from app.infrastructure.database import SessionLocal
from app.repositories.order_status_history_sqlalchemy import (
    create_order_status_history,
    list_order_status_history,
)
from app.repositories.orders_sqlalchemy import create_order
from app.schemas.order import (
    OrderCreate,
    OrderStatus,
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


def test_creates_order_status_history() -> None:
    internal_order_id = str(uuid4())

    order = OrderCreate.model_validate(order_payload("HISTORY-REPOSITORY-001"))

    with SessionLocal() as session:
        create_order(
            session=session,
            order=order,
            internal_order_id=internal_order_id,
            received_at=datetime.now(timezone.utc),
        )

        history = create_order_status_history(
            session=session,
            internal_order_id=internal_order_id,
            previous_status=OrderStatus.RECEIVED,
            new_status=OrderStatus.VALIDATING_INPUT,
        )

    assert history.id is not None
    assert history.internal_order_id == internal_order_id
    assert history.previous_status == "RECEIVED"
    assert history.new_status == "VALIDATING_INPUT"
    assert history.changed_at is not None


def test_lists_history_in_creation_order() -> None:
    internal_order_id = str(uuid4())

    order = OrderCreate.model_validate(order_payload("HISTORY-REPOSITORY-002"))

    with SessionLocal() as session:
        create_order(
            session=session,
            order=order,
            internal_order_id=internal_order_id,
            received_at=datetime.now(timezone.utc),
        )

        create_order_status_history(
            session=session,
            internal_order_id=internal_order_id,
            previous_status=OrderStatus.RECEIVED,
            new_status=OrderStatus.VALIDATING_INPUT,
        )

        create_order_status_history(
            session=session,
            internal_order_id=internal_order_id,
            previous_status=OrderStatus.VALIDATING_INPUT,
            new_status=OrderStatus.COMPLETED,
        )

        history = list_order_status_history(
            session=session,
            internal_order_id=internal_order_id,
        )

    assert len(history) == 2

    assert history[0].previous_status == "RECEIVED"
    assert history[0].new_status == "VALIDATING_INPUT"

    assert history[1].previous_status == "VALIDATING_INPUT"
    assert history[1].new_status == "COMPLETED"


def test_returns_empty_history_for_unknown_order() -> None:
    with SessionLocal() as session:
        history = list_order_status_history(
            session=session,
            internal_order_id=("00000000-0000-0000-0000-000000000000"),
        )

    assert history == []
