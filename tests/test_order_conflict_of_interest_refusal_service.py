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
from app.services.order_conflict_of_interest_refusal_service import (
    refuse_order_for_conflict_of_interest,
)


def order_payload(
    external_order_id: str,
    has_conflict: bool = True,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "external_order_id": external_order_id,
        "property": {
            "property_type": "APARTMENT",
            "state": "SP",
            "city": "São Paulo",
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

    if has_conflict:
        payload["conflict_of_interest"] = {
            "has_conflict": True,
            "conflict_type": "RELATED_PARTY",
            "description": (
                "Solicitante possui vínculo com o responsável pela avaliação."
            ),
            "identified_by": "COMPLIANCE",
        }

    return payload


def create_test_order(
    external_order_id: str,
    has_conflict: bool = True,
) -> tuple[str, OrderCreate]:
    internal_order_id = str(uuid4())
    order = OrderCreate.model_validate(
        order_payload(
            external_order_id=external_order_id,
            has_conflict=has_conflict,
        )
    )

    with SessionLocal() as session:
        create_order(
            session=session,
            order=order,
            internal_order_id=internal_order_id,
            received_at=datetime.now(timezone.utc),
        )

    return internal_order_id, order


def test_refuses_order_for_conflict_of_interest() -> None:
    internal_order_id, order = create_test_order(
        "CONFLICT-REFUSAL-001",
    )

    with SessionLocal() as session:
        result = refuse_order_for_conflict_of_interest(
            session=session,
            internal_order_id=internal_order_id,
            order=order,
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
    assert refusal.reason_code == OrderRefusalReason.CONFLICT_OF_INTEREST.value
    assert refusal.contract_reference == "TR §9.5(c) e §9.6"
    assert refusal.evidence["condition"] == "CONFLICT_OF_INTEREST_DECLARED"
    assert refusal.evidence["conflict_type"] == "RELATED_PARTY"
    assert refusal.evidence["identified_by"] == "COMPLIANCE"

    assert len(history) == 2
    assert history[0].previous_status == OrderStatus.RECEIVED.value
    assert history[0].new_status == OrderStatus.VALIDATING_INPUT.value
    assert history[1].previous_status == OrderStatus.VALIDATING_INPUT.value
    assert history[1].new_status == OrderStatus.REFUSED.value


def test_returns_none_when_there_is_no_conflict() -> None:
    internal_order_id, order = create_test_order(
        "CONFLICT-REFUSAL-002",
        has_conflict=False,
    )

    with SessionLocal() as session:
        result = refuse_order_for_conflict_of_interest(
            session=session,
            internal_order_id=internal_order_id,
            order=order,
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

    assert stored_order is not None
    assert stored_order.status == OrderStatus.RECEIVED
    assert refusal is None


def test_returns_none_for_unknown_order() -> None:
    order = OrderCreate.model_validate(
        order_payload("CONFLICT-REFUSAL-003"),
    )

    with SessionLocal() as session:
        result = refuse_order_for_conflict_of_interest(
            session=session,
            internal_order_id="00000000-0000-0000-0000-000000000000",
            order=order,
        )

    assert result is None
