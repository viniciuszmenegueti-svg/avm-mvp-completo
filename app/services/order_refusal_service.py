from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.repositories.order_refusals_sqlalchemy import (
    create_order_refusal,
    get_order_refusal_by_internal_order_id,
)
from app.repositories.order_status_history_sqlalchemy import (
    create_order_status_history,
)
from app.repositories.orders_sqlalchemy import (
    get_order_by_internal_id,
    update_order_status,
)
from app.schemas.order import OrderStatus
from app.schemas.order_refusal import (
    OrderRefusalCreate,
    OrderRefusalResponse,
)
from app.services.order_status import validate_order_status_transition
from app.services.order_status_update import resolve_audit_request_id


def refuse_order_with_evidence(
    session: Session,
    internal_order_id: str,
    refusal: OrderRefusalCreate,
    changed_by: str = "system",
    request_id: str | None = None,
    commit: bool = True,
) -> OrderRefusalResponse | None:
    order = get_order_by_internal_id(
        session=session,
        internal_order_id=internal_order_id,
    )

    if order is None:
        return None

    existing_refusal = get_order_refusal_by_internal_order_id(
        session=session,
        internal_order_id=internal_order_id,
    )

    if existing_refusal is not None:
        return OrderRefusalResponse.model_validate(existing_refusal)

    validate_order_status_transition(
        current_status=order.status,
        new_status=OrderStatus.REFUSED,
    )

    refused_at = datetime.now(timezone.utc)

    try:
        created_refusal = create_order_refusal(
            session=session,
            refusal_id=str(uuid4()),
            internal_order_id=internal_order_id,
            refusal=refusal,
            refused_at=refused_at,
            commit=False,
        )

        updated_order = update_order_status(
            session=session,
            internal_order_id=internal_order_id,
            new_status=OrderStatus.REFUSED,
            responded_at=refused_at,
            commit=False,
        )

        if updated_order is None:
            if commit:
                session.rollback()
            return None

        create_order_status_history(
            session=session,
            internal_order_id=internal_order_id,
            previous_status=order.status,
            new_status=OrderStatus.REFUSED,
            changed_by=changed_by,
            request_id=resolve_audit_request_id(request_id),
            reason_code=refusal.reason_code.value,
            context={
                "contract_reference": refusal.contract_reference,
                "condition": refusal.evidence.get("condition"),
            },
            commit=False,
        )

        if commit:
            session.commit()
            session.refresh(created_refusal)
        else:
            session.flush()

        return OrderRefusalResponse.model_validate(created_refusal)

    except Exception:
        if commit:
            session.rollback()
        raise
