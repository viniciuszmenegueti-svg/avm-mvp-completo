from datetime import datetime, timezone
from uuid import uuid4

from app.infrastructure.database import SessionLocal
from app.repositories.orders_sqlalchemy import (
    create_order,
    get_order_by_internal_id,
    update_order_status,
)
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


def test_updates_order_status() -> None:
    internal_order_id = str(uuid4())

    order = OrderCreate.model_validate(
        order_payload("STATUS-REPOSITORY-001")
    )

    with SessionLocal() as session:
        create_order(
            session=session,
            order=order,
            internal_order_id=internal_order_id,
            received_at=datetime.now(timezone.utc),
        )

        updated_order = update_order_status(
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

    assert stored_order is not None
    assert stored_order.status == (
        OrderStatus.VALIDATING_INPUT
    )


def test_returns_none_when_updating_unknown_order() -> None:
    with SessionLocal() as session:
        updated_order = update_order_status(
            session=session,
            internal_order_id=(
                "00000000-0000-0000-0000-000000000000"
            ),
            new_status=OrderStatus.VALIDATING_INPUT,
        )

    assert updated_order is None
