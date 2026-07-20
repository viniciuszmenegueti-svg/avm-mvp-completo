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
) -> OrderStatusHistoryModel:
    history = OrderStatusHistoryModel(
        internal_order_id=internal_order_id,
        previous_status=previous_status.value,
        new_status=new_status.value,
    )

    session.add(history)
    session.commit()
    session.refresh(history)

    return history


def list_order_status_history(
    session: Session,
    internal_order_id: str,
) -> list[OrderStatusHistoryModel]:
    statement = (
        select(OrderStatusHistoryModel)
        .where(
            OrderStatusHistoryModel.internal_order_id
            == internal_order_id
        )
        .order_by(
            OrderStatusHistoryModel.changed_at.asc(),
            OrderStatusHistoryModel.id.asc(),
        )
    )

    return list(
        session.scalars(statement).all()
    )
