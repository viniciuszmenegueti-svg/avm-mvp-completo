from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.domain.order_model import OrderModel
from app.repositories.order_refusals_sqlalchemy import (
    get_order_refusal_by_internal_order_id,
)
from app.repositories.orders_sqlalchemy import (
    ORDER_RESPONSE_SLA_SECONDS,
    get_order_by_internal_id,
    order_model_to_response,
)
from app.repositories.valuations_sqlalchemy import (
    get_valuation_by_internal_order_id,
)
from app.schemas.order import OrderResponse, OrderStatus
from app.schemas.order_processing import (
    OrderProcessOutcome,
    OrderProcessResponse,
)
from app.schemas.order_refusal import OrderRefusalResponse
from app.services.order_status_update import update_order_status_with_history
from app.services.valuation_service import calculate_and_store_valuation


class OrderProcessingStateError(Exception):
    def __init__(self, status: OrderStatus, message: str) -> None:
        self.status = status
        super().__init__(message)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _build_terminal_response(
    session: Session,
    order: OrderResponse,
) -> OrderProcessResponse:
    valuation = get_valuation_by_internal_order_id(
        session=session,
        internal_order_id=order.internal_order_id,
    )
    refusal_model = get_order_refusal_by_internal_order_id(
        session=session,
        internal_order_id=order.internal_order_id,
    )
    refusal = (
        None
        if refusal_model is None
        else OrderRefusalResponse.model_validate(refusal_model)
    )

    if order.status in {
        OrderStatus.COMPLETED,
        OrderStatus.DELIVERING,
        OrderStatus.DELIVERED,
    }:
        if valuation is None:
            raise OrderProcessingStateError(
                order.status,
                "A ordem concluída não possui avaliação persistida.",
            )
        outcome = OrderProcessOutcome.COMPLETED
    elif order.status == OrderStatus.REFUSED:
        if refusal is None:
            raise OrderProcessingStateError(
                order.status,
                "A ordem recusada não possui dossiê de recusa persistido.",
            )
        outcome = OrderProcessOutcome.REFUSED
    elif order.status == OrderStatus.CANCELLED:
        outcome = OrderProcessOutcome.CANCELLED
    else:
        raise OrderProcessingStateError(
            order.status,
            "A ordem não alcançou um resultado terminal auditável.",
        )

    return OrderProcessResponse(
        outcome=outcome,
        order=order,
        valuation=valuation,
        refusal=refusal,
        contractual_delivery_enabled=False,
    )


def process_order(
    session: Session,
    internal_order_id: str,
    changed_by: str,
    request_id: str,
    observed_at: datetime | None = None,
) -> OrderProcessResponse | None:
    database_order = session.get(
        OrderModel,
        internal_order_id,
        with_for_update=True,
    )
    if database_order is None:
        return None

    order = order_model_to_response(database_order)
    if order.status in {
        OrderStatus.COMPLETED,
        OrderStatus.DELIVERING,
        OrderStatus.DELIVERED,
        OrderStatus.REFUSED,
        OrderStatus.CANCELLED,
    }:
        return _build_terminal_response(session, order)

    now = _as_utc(observed_at or datetime.now(timezone.utc))
    deadline = _as_utc(order.response_deadline_at)
    if now > deadline:
        cancelled_order = update_order_status_with_history(
            session=session,
            internal_order_id=internal_order_id,
            new_status=OrderStatus.CANCELLED,
            changed_by=changed_by,
            request_id=request_id,
            reason_code="OS_TIMEOUT",
            context={
                "response_deadline_at": deadline.isoformat(),
                "timeout_detected_at": now.isoformat(),
                "maximum_response_seconds": ORDER_RESPONSE_SLA_SECONDS,
            },
            responded_at=now,
        )
        if cancelled_order is None:
            return None
        return _build_terminal_response(session, cancelled_order)

    next_status_by_current = {
        OrderStatus.RECEIVED: OrderStatus.VALIDATING_INPUT,
        OrderStatus.ACCEPTED: OrderStatus.QUEUED,
        OrderStatus.QUEUED: OrderStatus.PROCESSING,
        OrderStatus.FAILED: OrderStatus.QUEUED,
    }
    while order.status in next_status_by_current:
        next_status = next_status_by_current[order.status]
        updated_order = update_order_status_with_history(
            session=session,
            internal_order_id=internal_order_id,
            new_status=next_status,
            changed_by=changed_by,
            request_id=request_id,
            reason_code="AUTOMATIC_PROCESSING_STARTED",
            context={"endpoint": f"/orders/{internal_order_id}/process"},
            commit=False,
        )
        if updated_order is None:
            return None
        order = updated_order

    if order.status not in {OrderStatus.VALIDATING_INPUT, OrderStatus.PROCESSING}:
        raise OrderProcessingStateError(
            order.status,
            "O estado atual não permite o processamento automático da ordem.",
        )

    calculate_and_store_valuation(
        session=session,
        internal_order_id=internal_order_id,
        changed_by=changed_by,
        request_id=request_id,
    )
    processed_order = get_order_by_internal_id(
        session=session,
        internal_order_id=internal_order_id,
    )
    if processed_order is None:
        return None
    return _build_terminal_response(session, processed_order)
