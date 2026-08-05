from sqlalchemy.orm import Session

from app.repositories.orders_sqlalchemy import get_order_by_internal_id
from app.schemas.order import OrderCreate, OrderResponse, OrderStatus
from app.schemas.order_refusal import OrderRefusalCreate, OrderRefusalReason
from app.services.order_refusal_service import refuse_order_with_evidence
from app.services.order_status_update import update_order_status_with_history


def refuse_order_for_city_data_mismatch(
    session: Session,
    internal_order_id: str,
    order: OrderCreate,
    expected_city: str,
    expected_state: str,
    changed_by: str = "system",
    request_id: str | None = None,
    commit: bool = True,
) -> OrderResponse | None:
    try:
        validating_order = update_order_status_with_history(
            session=session,
            internal_order_id=internal_order_id,
            new_status=OrderStatus.VALIDATING_INPUT,
            changed_by=changed_by,
            request_id=request_id,
            reason_code="INPUT_VALIDATION_STARTED",
            context={"source": "city_registry_validation"},
            commit=False,
        )

        if validating_order is None:
            if commit:
                session.rollback()
            return None

        property_data = order.property

        refusal = OrderRefusalCreate(
            reason_code=OrderRefusalReason.DATA_INCONSISTENCY,
            contract_reference="TR §9.5(b) e §9.6",
            message=(
                "Foram detectadas informações incompatíveis nos dados de localização "
                "informados para o imóvel."
            ),
            evidence={
                "condition": "CITY_DATA_MISMATCH",
                "city_ibge_code": property_data.city_ibge_code,
                "informed_city": property_data.city,
                "informed_state": property_data.state,
                "expected_city": expected_city,
                "expected_state": expected_state,
            },
            details={
                "field_group": "property.location",
                "inconsistent_fields": [
                    "city",
                    "state",
                    "city_ibge_code",
                ],
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
