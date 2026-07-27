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
from app.schemas.order import OrderCreate, OrderStatus
from app.schemas.order_refusal import OrderRefusalReason
from app.services.order_data_inconsistency_refusal_service import (
    refuse_order_for_city_data_mismatch,
)


def order_payload(external_order_id: str) -> dict[str, object]:
    return {
        "external_order_id": external_order_id,
        "property": {
            "property_type": "APARTMENT",
            "state": "RJ",
            "city": "Rio de Janeiro",
            "city_ibge_code": "3550308",
            "postal_code": "01001-000",
            "neighborhood": "Centro",
            "street": "Rua de Teste",
            "number": "100",
            "complement": "Apartamento 10",
            "private_area_m2": 70,
            "built_area_m2": 80,
            "land_area_m2": None,
            "bedrooms": 2,
            "bathrooms": 2,
            "parking_spaces": 1,
        },
    }


def create_test_order(external_order_id: str) -> tuple[str, OrderCreate]:
    internal_order_id = str(uuid4())
    order = OrderCreate.model_validate(order_payload(external_order_id))

    with SessionLocal() as session:
        create_order(
            session=session,
            order=order,
            internal_order_id=internal_order_id,
            received_at=datetime.now(timezone.utc),
        )

    return internal_order_id, order


def test_refuses_order_for_city_data_mismatch() -> None:
    internal_order_id, order = create_test_order(
        "DATA-INCONSISTENCY-001",
    )

    with SessionLocal() as session:
        result = refuse_order_for_city_data_mismatch(
            session=session,
            internal_order_id=internal_order_id,
            order=order,
            expected_city="São Paulo",
            expected_state="SP",
        )

    assert result is not None
    assert result.status == OrderStatus.REFUSED

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
    assert refusal.reason_code == OrderRefusalReason.DATA_INCONSISTENCY.value
    assert refusal.contract_reference == "TR §9.5(b) e §9.6"
    assert refusal.evidence["condition"] == "CITY_DATA_MISMATCH"
    assert refusal.evidence["informed_city"] == "Rio de Janeiro"
    assert refusal.evidence["informed_state"] == "RJ"
    assert refusal.evidence["expected_city"] == "São Paulo"
    assert refusal.evidence["expected_state"] == "SP"

    assert len(history) == 2
    assert history[0].previous_status == OrderStatus.RECEIVED.value
    assert history[0].new_status == OrderStatus.VALIDATING_INPUT.value
    assert history[1].previous_status == OrderStatus.VALIDATING_INPUT.value
    assert history[1].new_status == OrderStatus.REFUSED.value


def test_returns_none_for_unknown_order() -> None:
    order = OrderCreate.model_validate(order_payload("DATA-INCONSISTENCY-002"))

    with SessionLocal() as session:
        result = refuse_order_for_city_data_mismatch(
            session=session,
            internal_order_id="00000000-0000-0000-0000-000000000000",
            order=order,
            expected_city="São Paulo",
            expected_state="SP",
        )

    assert result is None
