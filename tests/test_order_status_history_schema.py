from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.order import OrderStatus
from app.schemas.order_status_history import (
    OrderStatusHistoryResponse,
)


def valid_history_payload() -> dict:
    return {
        "id": 1,
        "internal_order_id": "00000000-0000-0000-0000-000000000001",
        "previous_status": "RECEIVED",
        "new_status": "VALIDATING_INPUT",
        "changed_at": datetime.now(timezone.utc),
        "changed_by": "caixa-integration",
        "request_id": "TRACE-STATUS-001",
        "reason_code": "CLIENT_STATUS_UPDATE",
        "context": {"source": "api"},
    }


def test_accepts_valid_status_history() -> None:
    history = OrderStatusHistoryResponse.model_validate(valid_history_payload())

    assert history.id == 1
    assert history.previous_status == OrderStatus.RECEIVED
    assert history.new_status == OrderStatus.VALIDATING_INPUT
    assert history.changed_at is not None
    assert history.changed_by == "caixa-integration"
    assert history.request_id == "TRACE-STATUS-001"
    assert history.reason_code == "CLIENT_STATUS_UPDATE"
    assert history.context == {"source": "api"}


def test_rejects_invalid_previous_status() -> None:
    payload = valid_history_payload()
    payload["previous_status"] = "UNKNOWN_STATUS"

    with pytest.raises(ValidationError):
        OrderStatusHistoryResponse.model_validate(payload)


def test_rejects_invalid_new_status() -> None:
    payload = valid_history_payload()
    payload["new_status"] = "UNKNOWN_STATUS"

    with pytest.raises(ValidationError):
        OrderStatusHistoryResponse.model_validate(payload)


def test_rejects_invalid_history_id() -> None:
    payload = valid_history_payload()
    payload["id"] = 0

    with pytest.raises(ValidationError):
        OrderStatusHistoryResponse.model_validate(payload)
