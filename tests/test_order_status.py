from app.schemas.order import OrderStatus
from app.services.order_status import (
    can_transition_order_status,
)


def test_allows_received_to_validating_input() -> None:
    assert can_transition_order_status(
        current_status=OrderStatus.RECEIVED,
        new_status=OrderStatus.VALIDATING_INPUT,
    )


def test_allows_validating_input_to_completed() -> None:
    assert can_transition_order_status(
        current_status=OrderStatus.VALIDATING_INPUT,
        new_status=OrderStatus.COMPLETED,
    )


def test_allows_validating_input_to_refused() -> None:
    assert can_transition_order_status(
        current_status=OrderStatus.VALIDATING_INPUT,
        new_status=OrderStatus.REFUSED,
    )


def test_rejects_completed_to_received() -> None:
    assert not can_transition_order_status(
        current_status=OrderStatus.COMPLETED,
        new_status=OrderStatus.RECEIVED,
    )


def test_rejects_refused_to_validating_input() -> None:
    assert not can_transition_order_status(
        current_status=OrderStatus.REFUSED,
        new_status=OrderStatus.VALIDATING_INPUT,
    )


def test_rejects_transition_to_same_status() -> None:
    assert not can_transition_order_status(
        current_status=OrderStatus.RECEIVED,
        new_status=OrderStatus.RECEIVED,
    )
