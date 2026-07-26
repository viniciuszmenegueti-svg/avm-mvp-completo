import json
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.order_model import OrderModel
from app.domain.property_model import PropertyModel
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderStatus,
)
from app.schemas.property import (
    PropertyInput,
    PropertyType,
)


def create_order(
    session: Session,
    order: OrderCreate,
    internal_order_id: str,
    received_at: datetime,
    property_asset_id: str | None = None,
) -> OrderResponse:
    database_order = OrderModel(
        internal_order_id=internal_order_id,
        external_order_id=order.external_order_id,
        status=OrderStatus.RECEIVED.value,
        received_at=received_at,
        property_asset_id=property_asset_id,
        property_json=order.property.model_dump_json(),
    )

    database_order.property_record = PropertyModel(
        internal_order_id=internal_order_id,
        property_type=order.property.property_type.value,
        state=order.property.state,
        city=order.property.city,
        city_ibge_code=order.property.city_ibge_code,
        postal_code=order.property.postal_code,
        neighborhood=order.property.neighborhood,
        street=order.property.street,
        number=order.property.number,
        complement=order.property.complement,
        private_area_m2=order.property.private_area_m2,
        built_area_m2=order.property.built_area_m2,
        land_area_m2=order.property.land_area_m2,
        bedrooms=order.property.bedrooms,
        bathrooms=order.property.bathrooms,
        parking_spaces=order.property.parking_spaces,
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


def list_orders(
    session: Session,
    limit: int,
    offset: int,
    order_status: OrderStatus | None = None,
) -> tuple[list[OrderResponse], int]:
    filters = []

    if order_status is not None:
        filters.append(OrderModel.status == order_status.value)

    total_statement = select(func.count(OrderModel.internal_order_id)).where(*filters)

    total = session.scalar(total_statement) or 0

    statement = (
        select(OrderModel)
        .where(*filters)
        .order_by(OrderModel.received_at.desc())
        .limit(limit)
        .offset(offset)
    )

    database_orders = session.scalars(statement).all()

    orders = [
        order_model_to_response(database_order) for database_order in database_orders
    ]

    return orders, total


def order_model_to_response(
    database_order: OrderModel,
) -> OrderResponse:
    if database_order.property_record is not None:
        property_data = property_model_to_input(database_order.property_record)
    else:
        property_data = PropertyInput.model_validate(
            json.loads(database_order.property_json)
        )

    return OrderResponse(
        internal_order_id=database_order.internal_order_id,
        external_order_id=database_order.external_order_id,
        status=OrderStatus(database_order.status),
        received_at=database_order.received_at,
        property=property_data,
    )


def decimal_to_float(
    value: Decimal | None,
) -> float | None:
    if value is None:
        return None

    return float(value)


def property_model_to_input(
    database_property: PropertyModel,
) -> PropertyInput:
    return PropertyInput(
        property_type=PropertyType(database_property.property_type),
        state=database_property.state,
        city=database_property.city,
        city_ibge_code=database_property.city_ibge_code,
        postal_code=database_property.postal_code,
        neighborhood=database_property.neighborhood,
        street=database_property.street,
        number=database_property.number,
        complement=database_property.complement,
        private_area_m2=decimal_to_float(database_property.private_area_m2),
        built_area_m2=decimal_to_float(database_property.built_area_m2),
        land_area_m2=decimal_to_float(database_property.land_area_m2),
        bedrooms=database_property.bedrooms,
        bathrooms=database_property.bathrooms,
        parking_spaces=database_property.parking_spaces,
    )


def update_order_status(
    session: Session,
    internal_order_id: str,
    new_status: OrderStatus,
    commit: bool = True,
) -> OrderResponse | None:
    database_order = session.get(
        OrderModel,
        internal_order_id,
    )

    if database_order is None:
        return None

    database_order.status = new_status.value

    if commit:
        session.commit()
        session.refresh(database_order)
    else:
        session.flush()

    return order_model_to_response(database_order)
