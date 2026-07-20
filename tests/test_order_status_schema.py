import pytest
from pydantic import ValidationError

from app.schemas.order import (
    OrderStatus,
    OrderStatusUpdate,
)


def test_accepts_valid_order_status_update() -> None:
    status_update = OrderStatusUpdate.model_validate(
        {
            "status": "VALIDATING_INPUT",
        }
    )

    assert status_update.status == (OrderStatus.VALIDATING_INPUT)


def test_rejects_invalid_order_status_update() -> None:
    with pytest.raises(ValidationError):
        OrderStatusUpdate.model_validate(
            {
                "status": "PROCESSING",
            }
        )


def test_rejects_missing_status() -> None:
    with pytest.raises(ValidationError):
        OrderStatusUpdate.model_validate({})
