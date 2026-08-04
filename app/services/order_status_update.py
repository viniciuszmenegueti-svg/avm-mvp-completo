from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.request_id import get_request_id
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
    changed_by: str = "system",
    request_id: str | None = None,
    reason_code: str = "STATUS_TRANSITION",
    context: dict[str, Any] | None = None,
    responded_at: datetime | None = None,
    commit: bool = True,
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
            responded_at=responded_at,
            commit=False,
        )

        if updated_order is None:
            if commit:
                session.rollback()
            return None

        create_order_status_history(
            session=session,
            internal_order_id=internal_order_id,
            previous_status=existing_order.status,
            new_status=new_status,
            changed_by=changed_by,
            request_id=resolve_audit_request_id(request_id),
            reason_code=reason_code,
            context=context,
            commit=False,
        )

        if commit:
            session.commit()
        else:
            session.flush()

        return updated_order

    except InvalidOrderStatusTransitionError:
        if commit:
            session.rollback()
        raise
    except Exception:
        if commit:
            session.rollback()
        raise


def resolve_audit_request_id(request_id: str | None) -> str:
    value = request_id or get_request_id()
    if not value or value == "-":
        return "internal"
    return value[:128]
