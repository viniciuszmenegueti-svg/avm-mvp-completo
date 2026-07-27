from sqlalchemy.orm import Session

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
) -> OrderResponse | None:
    validating_order = update_order_status_with_history(
        session=session,
        internal_order_id=internal_order_id,
        new_status=OrderStatus.VALIDATING_INPUT,
    )

    if validating_order is None:
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
    )

    if refusal_result is None:
        return None

    return validating_order.model_copy(
        update={
            "status": OrderStatus.REFUSED,
        }
    )
