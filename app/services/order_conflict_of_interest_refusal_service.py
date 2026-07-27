from sqlalchemy.orm import Session

from app.schemas.order import OrderCreate, OrderResponse, OrderStatus
from app.schemas.order_refusal import OrderRefusalCreate, OrderRefusalReason
from app.services.order_refusal_service import refuse_order_with_evidence
from app.services.order_status_update import update_order_status_with_history


def refuse_order_for_conflict_of_interest(
    session: Session,
    internal_order_id: str,
    order: OrderCreate,
) -> OrderResponse | None:
    declaration = order.conflict_of_interest

    if not declaration.has_conflict:
        return None

    validating_order = update_order_status_with_history(
        session=session,
        internal_order_id=internal_order_id,
        new_status=OrderStatus.VALIDATING_INPUT,
    )

    if validating_order is None:
        return None

    refusal = OrderRefusalCreate(
        reason_code=OrderRefusalReason.CONFLICT_OF_INTEREST,
        contract_reference="TR §9.5(c) e §9.6",
        message=(
            "Foi identificado conflito de interesse incompatível com "
            "a execução independente da avaliação."
        ),
        evidence={
            "condition": "CONFLICT_OF_INTEREST_DECLARED",
            "conflict_type": declaration.conflict_type,
            "description": declaration.description,
            "identified_by": declaration.identified_by,
        },
        details={
            "declaration_source": "order.conflict_of_interest",
            "has_conflict": declaration.has_conflict,
        },
        model_version=None,
        dataset_version=None,
    )

    refusal_result = refuse_order_with_evidence(
        session=session,
        internal_order_id=internal_order_id,
        refusal=refusal,
    )

    if refusal_result is None:
        return None

    return validating_order.model_copy(
        update={
            "status": OrderStatus.REFUSED,
        }
    )
