from datetime import datetime, timezone
from uuid import uuid4

from app.infrastructure.database import SessionLocal
from app.repositories.order_refusals_sqlalchemy import (
    get_order_refusal_by_internal_order_id,
)
from app.repositories.order_status_history_sqlalchemy import (
    list_order_status_history,
)
from app.repositories.orders_sqlalchemy import (
    create_order,
    get_order_by_internal_id,
)
from app.schemas.order import (
    OrderCreate,
    OrderStatus,
)
from app.services.order_status_update import (
    update_order_status_with_history,
)
from app.services.valuation_service import (
    calculate_and_store_valuation,
)


def order_payload(
    external_order_id: str,
) -> dict[str, object]:
    return {
        "external_order_id": external_order_id,
        "property": {
            "property_type": "HOUSE",
            "state": "RJ",
            "city": "Rio de Janeiro",
            "city_ibge_code": "3304557",
            "postal_code": "20010-000",
            "neighborhood": "Centro",
            "street": "Rua de Teste",
            "number": "100",
            "complement": None,
            "private_area_m2": 120,
            "built_area_m2": 140,
            "land_area_m2": 200,
            "bedrooms": 3,
            "bathrooms": 2,
            "parking_spaces": 2,
        },
    }


def create_test_order(
    external_order_id: str,
) -> str:
    internal_order_id = str(uuid4())

    order = OrderCreate.model_validate(order_payload(external_order_id))

    with SessionLocal() as session:
        create_order(
            session=session,
            order=order,
            internal_order_id=internal_order_id,
            received_at=datetime.now(timezone.utc),
        )

    with SessionLocal() as session:
        updated_order = update_order_status_with_history(
            session=session,
            internal_order_id=internal_order_id,
            new_status=OrderStatus.VALIDATING_INPUT,
        )

    assert updated_order is not None
    assert updated_order.status == OrderStatus.VALIDATING_INPUT

    return internal_order_id


def test_refuses_order_when_base_price_is_missing() -> None:
    internal_order_id = create_test_order("VALUATION-REFUSAL-001")

    with SessionLocal() as session:
        result = calculate_and_store_valuation(
            session=session,
            internal_order_id=internal_order_id,
        )

    assert result is None

    with SessionLocal() as session:
        stored_order = get_order_by_internal_id(
            session=session,
            internal_order_id=internal_order_id,
        )

        refusal = get_order_refusal_by_internal_order_id(
            session=session,
            internal_order_id=internal_order_id,
        )

        history = list_order_status_history(
            session=session,
            internal_order_id=internal_order_id,
        )

    assert stored_order is not None
    assert stored_order.status == OrderStatus.REFUSED

    assert refusal is not None
    assert refusal.reason_code == "TR_9_5_A"
    assert refusal.message == (
        "O modelo estatístico não permite precificar o imóvel: "
        "não há modelo/dataset aplicável à cidade e tipologia."
    )
    assert refusal.details == {
        "city_ibge_code": "3304557",
        "property_type": "HOUSE",
        "pricing_method": "RULE_BASED_V1",
        "execution_mode": "DEMONSTRATION",
    }
    assert refusal.contract_reference == "TR §9.5(a) e §9.6"
    assert refusal.evidence["condition"] == "MODEL_OR_DATASET_UNAVAILABLE"
    assert refusal.refused_at is not None

    assert len(history) == 2

    assert history[0].previous_status == "RECEIVED"
    assert history[0].new_status == "VALIDATING_INPUT"

    assert history[1].previous_status == "VALIDATING_INPUT"
    assert history[1].new_status == "REFUSED"
