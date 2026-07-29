from sqlalchemy.orm import Session

from app.schemas.order import OrderCreate, OrderResponse, OrderStatus
from app.schemas.order_refusal import OrderRefusalCreate, OrderRefusalReason
from app.services.order_refusal_service import refuse_order_with_evidence
from app.services.order_status_update import update_order_status_with_history


def refuse_order_for_unconfirmed_location(
    session: Session,
    internal_order_id: str,
    order: OrderCreate,
    commit: bool = True,
) -> OrderResponse | None:
    declaration = order.location_confirmation

    if declaration.meets_contract_accuracy:
        return None

    try:
        validating_order = update_order_status_with_history(
            session=session,
            internal_order_id=internal_order_id,
            new_status=OrderStatus.VALIDATING_INPUT,
            commit=False,
        )

        if validating_order is None:
            if commit:
                session.rollback()
            return None

        refusal = OrderRefusalCreate(
            reason_code=OrderRefusalReason.LOCATION_NOT_CONFIRMED,
            contract_reference="TR §9.5(d) e §9.6",
            message=(
                "A localização do imóvel não pôde ser confirmada por evidência "
                "suficiente para a execução da avaliação."
            ),
            evidence={
                "condition": "LOCATION_NOT_CONFIRMED",
                "confirmation_method": declaration.confirmation_method,
                "evidence_reference": declaration.evidence_reference,
                "failure_reason": declaration.failure_reason,
                "verified_by": declaration.verified_by,
                **(
                    {
                        "latitude": declaration.latitude,
                        "longitude": declaration.longitude,
                        "accuracy_meters": declaration.accuracy_meters,
                        "maximum_accuracy_meters": (
                            declaration.MAXIMUM_CONTRACT_ACCURACY_METERS
                        ),
                    }
                    if declaration.accuracy_meters is not None
                    else {}
                ),
            },
            details={
                "declaration_source": "order.location_confirmation",
                "is_confirmed": declaration.is_confirmed,
                "meets_contract_accuracy": declaration.meets_contract_accuracy,
            },
            model_version=None,
            dataset_version=None,
        )

        refusal_result = refuse_order_with_evidence(
            session=session,
            internal_order_id=internal_order_id,
            refusal=refusal,
            commit=False,
        )

        if refusal_result is None:
            if commit:
                session.rollback()
            return None

        refused_order = validating_order.model_copy(
            update={
                "status": OrderStatus.REFUSED,
            }
        )

        if commit:
            session.commit()
        else:
            session.flush()

        return refused_order

    except Exception:
        if commit:
            session.rollback()
        raise
