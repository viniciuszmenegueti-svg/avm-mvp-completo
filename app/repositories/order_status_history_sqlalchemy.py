import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.order_status_history_model import (
    OrderStatusHistoryModel,
)
from app.schemas.order import OrderStatus


def create_order_status_history(
    session: Session,
    internal_order_id: str,
    previous_status: OrderStatus,
    new_status: OrderStatus,
    changed_by: str = "system",
    request_id: str = "internal",
    reason_code: str = "STATUS_TRANSITION",
    context: dict[str, Any] | None = None,
    commit: bool = True,
) -> OrderStatusHistoryModel:
    history = OrderStatusHistoryModel(
        internal_order_id=internal_order_id,
        previous_status=previous_status.value,
        new_status=new_status.value,
        changed_by=changed_by,
        request_id=request_id,
        reason_code=reason_code,
        context_json=json.dumps(
            context or {},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
    )

    session.add(history)

    if commit:
        session.commit()
        session.refresh(history)
    else:
        session.flush()

    return history


def list_order_status_history(
    session: Session,
    internal_order_id: str,
) -> list[OrderStatusHistoryModel]:
    statement = (
        select(OrderStatusHistoryModel)
        .where(OrderStatusHistoryModel.internal_order_id == internal_order_id)
        .order_by(
            OrderStatusHistoryModel.changed_at.asc(),
            OrderStatusHistoryModel.id.asc(),
        )
    )

    return list(session.scalars(statement).all())
