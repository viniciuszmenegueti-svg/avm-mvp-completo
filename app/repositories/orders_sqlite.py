import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.order_model import OrderModel
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderStatus,
)
from app.schemas.property import PropertyInput


def create_order(
    session: Session,
    order: OrderCreate,
    internal_order_id: str,
    received_at,
) -> OrderResponse:
    database_order = OrderModel(
        internal_order_id=internal_order_id,
        external_order_id=order.external_order_id,
        status=OrderStatus.RECEIVED.value,
        received_at=received_at,
        property_json=order.property.model_dump_json(),
    )

    session.add(database_order)
    session.commit()
    session.refresh(database_order)

    return order_model_to_response(database_order)


def get_order_by_internal_id(
    session: Session,
    internal_order_id: str,
) -> OrderResponse | None:
    database_order = session.get(
        OrderModel,
        internal_order_id,
    )

    if database_order is None:
        return None

    return order_model_to_response(database_order)


def get_order_by_external_id(
    session: Session,
    external_order_id: str,
) -> OrderResponse | None:
    statement = select(OrderModel).where(
        OrderModel.external_order_id == external_order_id
    )

    database_order = session.scalar(statement)

    if database_order is None:
        return None

    return order_model_to_response(database_order)


def order_model_to_response(
    database_order: OrderModel,
) -> OrderResponse:
    property_data = json.loads(
        database_order.property_json
    )

    return OrderResponse(
        internal_order_id=database_order.internal_order_id,
        external_order_id=database_order.external_order_id,
        status=OrderStatus(database_order.status),
        received_at=database_order.received_at,
        property=PropertyInput(**property_data),
    )
