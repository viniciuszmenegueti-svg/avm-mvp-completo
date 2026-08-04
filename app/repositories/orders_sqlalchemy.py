import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.order_model import OrderModel
from app.domain.property_model import PropertyModel
from app.schemas.order import (
    LocationConfirmationDeclaration,
    OrderCreate,
    OrderResponse,
    OrderSlaOutcome,
    OrderStatus,
)
from app.schemas.property import (
    PropertyInput,
    PropertyType,
)


ORDER_RESPONSE_SLA_SECONDS = 300
TERMINAL_RESPONSE_STATUSES = frozenset(
    {
        OrderStatus.COMPLETED,
        OrderStatus.REFUSED,
        OrderStatus.CANCELLED,
    }
)


def create_order(
    session: Session,
    order: OrderCreate,
    internal_order_id: str,
    received_at: datetime,
    property_asset_id: str | None = None,
    commit: bool = True,
) -> OrderResponse:
    database_order = OrderModel(
        internal_order_id=internal_order_id,
        external_order_id=order.external_order_id,
        status=OrderStatus.RECEIVED.value,
        received_at=received_at,
        response_deadline_at=received_at
        + timedelta(seconds=ORDER_RESPONSE_SLA_SECONDS),
        responded_at=None,
        property_asset_id=property_asset_id,
        property_json=order.property.model_dump_json(),
        location_is_confirmed=order.location_confirmation.is_confirmed,
        location_confirmation_method=(order.location_confirmation.confirmation_method),
        location_evidence_reference=(order.location_confirmation.evidence_reference),
        location_failure_reason=order.location_confirmation.failure_reason,
        location_verified_by=order.location_confirmation.verified_by,
        latitude=order.location_confirmation.latitude,
        longitude=order.location_confirmation.longitude,
        location_accuracy_meters=order.location_confirmation.accuracy_meters,
        geocoding_audit_id=order.location_confirmation.geocoding_audit_id,
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

    if commit:
        session.commit()
        session.refresh(database_order)
    else:
        session.flush()

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

    location_confirmation = location_model_to_declaration(database_order)
    received_at = _as_utc(database_order.received_at)
    response_deadline_at = _as_utc(database_order.response_deadline_at)
    responded_at = (
        None
        if database_order.responded_at is None
        else _as_utc(database_order.responded_at)
    )
    elapsed_seconds, sla_outcome = calculate_response_sla(
        received_at=received_at,
        response_deadline_at=response_deadline_at,
        responded_at=responded_at,
    )

    return OrderResponse(
        internal_order_id=database_order.internal_order_id,
        external_order_id=database_order.external_order_id,
        status=OrderStatus(database_order.status),
        received_at=received_at,
        response_deadline_at=response_deadline_at,
        responded_at=responded_at,
        response_elapsed_seconds=elapsed_seconds,
        sla_outcome=sla_outcome,
        property=property_data,
        location_confirmation=location_confirmation,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def calculate_response_sla(
    received_at: datetime,
    response_deadline_at: datetime,
    responded_at: datetime | None,
    observed_at: datetime | None = None,
) -> tuple[float, OrderSlaOutcome]:
    received_utc = _as_utc(received_at)
    deadline_utc = _as_utc(response_deadline_at)
    effective_at = _as_utc(responded_at or observed_at or datetime.now(timezone.utc))
    elapsed_seconds = max(0.0, (effective_at - received_utc).total_seconds())

    if responded_at is None and effective_at <= deadline_utc:
        outcome = OrderSlaOutcome.PENDING
    elif effective_at <= deadline_utc:
        outcome = OrderSlaOutcome.WITHIN_SLA
    else:
        outcome = OrderSlaOutcome.BREACHED

    return round(elapsed_seconds, 3), outcome


def location_model_to_declaration(
    database_order: OrderModel,
) -> LocationConfirmationDeclaration:
    if database_order.location_is_confirmed is None:
        return LocationConfirmationDeclaration()

    return LocationConfirmationDeclaration(
        is_confirmed=database_order.location_is_confirmed,
        confirmation_method=database_order.location_confirmation_method,
        evidence_reference=database_order.location_evidence_reference,
        failure_reason=database_order.location_failure_reason,
        verified_by=database_order.location_verified_by,
        latitude=decimal_to_float(database_order.latitude),
        longitude=decimal_to_float(database_order.longitude),
        accuracy_meters=decimal_to_float(database_order.location_accuracy_meters),
        geocoding_audit_id=database_order.geocoding_audit_id,
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
    responded_at: datetime | None = None,
    commit: bool = True,
) -> OrderResponse | None:
    database_order = session.get(
        OrderModel,
        internal_order_id,
    )

    if database_order is None:
        return None

    database_order.status = new_status.value
    if new_status in TERMINAL_RESPONSE_STATUSES and database_order.responded_at is None:
        database_order.responded_at = responded_at or datetime.now(timezone.utc)

    if commit:
        session.commit()
        session.refresh(database_order)
    else:
        session.flush()

    return order_model_to_response(database_order)
