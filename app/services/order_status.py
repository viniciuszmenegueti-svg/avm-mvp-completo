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
    },
    OrderStatus.VALIDATING_INPUT: {
        OrderStatus.COMPLETED,
        OrderStatus.REFUSED,
    },
    OrderStatus.COMPLETED: set(),
    OrderStatus.REFUSED: set(),
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
