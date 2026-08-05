from sqlalchemy.orm import Session

from app.repositories.orders_sqlalchemy import get_order_by_internal_id
from app.schemas.order import OrderCreate, OrderResponse, OrderStatus
from app.schemas.order_refusal import OrderRefusalCreate, OrderRefusalReason
from app.services.order_refusal_service import refuse_order_with_evidence
from app.services.order_status_update import update_order_status_with_history


def refuse_order_for_unconfirmed_location(
    session: Session,
    internal_order_id: str,
    order: OrderCreate,
    commit: bool = True,
    require_auditable: bool = False,
    changed_by: str = "system",
    request_id: str | None = None,
) -> OrderResponse | None:
    declaration = order.location_confirmation

    location_acceptable = (
        declaration.has_auditable_contract_coordinates
        if require_auditable
        else declaration.meets_contract_accuracy
    )
    if location_acceptable:
        return None

    try:
        validating_order = update_order_status_with_history(
            session=session,
            internal_order_id=internal_order_id,
            new_status=OrderStatus.VALIDATING_INPUT,
            changed_by=changed_by,
            request_id=request_id,
            reason_code="INPUT_VALIDATION_STARTED",
            context={"source": "location_confirmation"},
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
                "condition": (
                    "LOCATION_NOT_AUDITABLE"
                    if require_auditable and declaration.is_confirmed
                    else "LOCATION_NOT_CONFIRMED"
                ),
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
                "has_auditable_contract_coordinates": (
                    declaration.has_auditable_contract_coordinates
                ),
                "auditable_location_required": require_auditable,
            },
            model_version=None,
            dataset_version=None,
        )

        refusal_result = refuse_order_with_evidence(
            session=session,
            internal_order_id=internal_order_id,
            refusal=refusal,
            changed_by=changed_by,
            request_id=request_id,
            commit=False,
        )

        if refusal_result is None:
            if commit:
                session.rollback()
            return None

        if commit:
            session.commit()
        else:
            session.flush()

        return get_order_by_internal_id(session, internal_order_id)

    except Exception:
        if commit:
            session.rollback()
        raise
