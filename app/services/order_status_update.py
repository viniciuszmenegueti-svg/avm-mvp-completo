from sqlalchemy.orm import Session

from app.domain.exceptions import (
    InvalidOrderStatusTransitionError,
)
from app.repositories.order_status_history_sqlalchemy import (
    create_order_status_history,
)
from app.repositories.orders_sqlalchemy import (
    get_order_by_internal_id,
    update_order_status,
)
from app.schemas.order import (
    OrderResponse,
    OrderStatus,
)
from app.services.order_status import (
    validate_order_status_transition,
)


def update_order_status_with_history(
    session: Session,
    internal_order_id: str,
    new_status: OrderStatus,
) -> OrderResponse | None:
    existing_order = get_order_by_internal_id(
        session=session,
        internal_order_id=internal_order_id,
    )

    if existing_order is None:
        return None

    validate_order_status_transition(
        current_status=existing_order.status,
        new_status=new_status,
    )

    try:
        updated_order = update_order_status(
            session=session,
            internal_order_id=internal_order_id,
            new_status=new_status,
            commit=False,
        )

        if updated_order is None:
            session.rollback()
            return None

        create_order_status_history(
            session=session,
            internal_order_id=internal_order_id,
            previous_status=existing_order.status,
            new_status=new_status,
            commit=False,
        )

        session.commit()

        return updated_order

    except InvalidOrderStatusTransitionError:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise
