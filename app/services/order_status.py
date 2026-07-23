from app.domain.exceptions import (
    InvalidOrderStatusTransitionError,
)
from app.schemas.order import OrderStatus


ALLOWED_STATUS_TRANSITIONS: dict[
    OrderStatus,
    set[OrderStatus],
] = {
    OrderStatus.RECEIVED: {
        OrderStatus.VALIDATING_INPUT,
        OrderStatus.CANCELLED,
    },
    OrderStatus.VALIDATING_INPUT: {
        OrderStatus.ACCEPTED,
        OrderStatus.COMPLETED,
        OrderStatus.REFUSED,
        OrderStatus.CANCELLED,
    },
    OrderStatus.ACCEPTED: {
        OrderStatus.QUEUED,
        OrderStatus.CANCELLED,
    },
    OrderStatus.QUEUED: {
        OrderStatus.PROCESSING,
        OrderStatus.CANCELLED,
    },
    OrderStatus.PROCESSING: {
        OrderStatus.COMPLETED,
        OrderStatus.FAILED,
        OrderStatus.CANCELLED,
    },
    OrderStatus.COMPLETED: {
        OrderStatus.DELIVERING,
    },
    OrderStatus.DELIVERING: {
        OrderStatus.DELIVERED,
        OrderStatus.FAILED,
    },
    OrderStatus.FAILED: {
        OrderStatus.QUEUED,
        OrderStatus.CANCELLED,
    },
    OrderStatus.DELIVERED: set(),
    OrderStatus.REFUSED: set(),
    OrderStatus.CANCELLED: set(),
}


def can_transition_order_status(
    current_status: OrderStatus,
    new_status: OrderStatus,
) -> bool:
    return new_status in ALLOWED_STATUS_TRANSITIONS[current_status]


def validate_order_status_transition(
    current_status: OrderStatus,
    new_status: OrderStatus,
) -> None:
    if can_transition_order_status(
        current_status=current_status,
        new_status=new_status,
    ):
        return

    raise InvalidOrderStatusTransitionError(
        current_status=current_status.value,
        new_status=new_status.value,
    )
