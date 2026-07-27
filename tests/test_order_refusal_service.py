from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.domain.exceptions import InvalidOrderStatusTransitionError
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
from app.schemas.order_refusal import (
    OrderRefusalCreate,
    OrderRefusalReason,
)
from app.services.order_refusal_service import refuse_order_with_evidence
from app.services.order_status_update import update_order_status_with_history


def order_payload(external_order_id: str) -> dict[str, object]:
    return {
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


def create_test_order(
    external_order_id: str,
    status: OrderStatus = OrderStatus.VALIDATING_INPUT,
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

    if status != OrderStatus.RECEIVED:
        with SessionLocal() as session:
            updated_order = update_order_status_with_history(
                session=session,
                internal_order_id=internal_order_id,
                new_status=status,
            )

        assert updated_order is not None

    return internal_order_id


def refusal_payload() -> OrderRefusalCreate:
    return OrderRefusalCreate(
        reason_code=OrderRefusalReason.DATA_INCONSISTENCY,
        contract_reference="TR §9.5(b) e §9.6",
        message="Foram detectadas informações incompatíveis nos dados do imóvel.",
        evidence={
            "condition": "PROPERTY_DATA_INCONSISTENCY",
            "fields": ["city", "state"],
        },
    )


def test_refuses_order_and_persists_evidence() -> None:
    internal_order_id = create_test_order("REFUSAL-SERVICE-001")

    with SessionLocal() as session:
        result = refuse_order_with_evidence(
            session=session,
            internal_order_id=internal_order_id,
            refusal=refusal_payload(),
        )

    assert result is not None
    assert result.reason_code == OrderRefusalReason.DATA_INCONSISTENCY
    assert result.contract_reference == "TR §9.5(b) e §9.6"
    assert result.evidence["condition"] == "PROPERTY_DATA_INCONSISTENCY"

    with SessionLocal() as session:
        order = get_order_by_internal_id(
            session=session,
            internal_order_id=internal_order_id,
        )
        stored_refusal = get_order_refusal_by_internal_order_id(
            session=session,
            internal_order_id=internal_order_id,
        )
        history = list_order_status_history(
            session=session,
            internal_order_id=internal_order_id,
        )

    assert order is not None
    assert order.status == OrderStatus.REFUSED
    assert stored_refusal is not None
    assert stored_refusal.reason_code == "TR_9_5_B"
    assert history[-1].new_status == "REFUSED"


def test_returns_none_for_unknown_order() -> None:
    with SessionLocal() as session:
        result = refuse_order_with_evidence(
            session=session,
            internal_order_id="00000000-0000-0000-0000-000000000000",
            refusal=refusal_payload(),
        )

    assert result is None


def test_returns_existing_refusal_idempotently() -> None:
    internal_order_id = create_test_order("REFUSAL-SERVICE-002")

    with SessionLocal() as session:
        first_result = refuse_order_with_evidence(
            session=session,
            internal_order_id=internal_order_id,
            refusal=refusal_payload(),
        )

    with SessionLocal() as session:
        second_result = refuse_order_with_evidence(
            session=session,
            internal_order_id=internal_order_id,
            refusal=refusal_payload(),
        )

    assert first_result is not None
    assert second_result is not None
    assert second_result.refusal_id == first_result.refusal_id


def test_rejects_refusal_from_invalid_status() -> None:
    internal_order_id = create_test_order(
        "REFUSAL-SERVICE-003",
        status=OrderStatus.RECEIVED,
    )

    with SessionLocal() as session:
        with pytest.raises(InvalidOrderStatusTransitionError):
            refuse_order_with_evidence(
                session=session,
                internal_order_id=internal_order_id,
                refusal=refusal_payload(),
            )


def test_rolls_back_when_order_update_returns_none() -> None:
    internal_order_id = create_test_order("REFUSAL-SERVICE-004")

    with SessionLocal() as session:
        with (
            patch(
                "app.services.order_refusal_service.update_order_status",
                return_value=None,
            ),
            patch.object(
                session,
                "rollback",
                wraps=session.rollback,
            ) as rollback_mock,
        ):
            result = refuse_order_with_evidence(
                session=session,
                internal_order_id=internal_order_id,
                refusal=refusal_payload(),
            )

    assert result is None
    rollback_mock.assert_called_once()


def test_rolls_back_when_history_creation_fails() -> None:
    internal_order_id = create_test_order("REFUSAL-SERVICE-005")

    with SessionLocal() as session:
        with (
            patch(
                "app.services.order_refusal_service.create_order_status_history",
                side_effect=RuntimeError("falha de teste"),
            ),
            patch.object(
                session,
                "rollback",
                wraps=session.rollback,
            ) as rollback_mock,
            pytest.raises(RuntimeError, match="falha de teste"),
        ):
            refuse_order_with_evidence(
                session=session,
                internal_order_id=internal_order_id,
                refusal=refusal_payload(),
            )

    rollback_mock.assert_called_once()
