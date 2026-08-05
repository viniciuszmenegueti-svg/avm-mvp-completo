from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.domain.exceptions import InvalidOrderStatusTransitionError
from app.domain.order_model import OrderModel
from app.domain.order_status_history_model import OrderStatusHistoryModel
from app.infrastructure.database import SessionLocal
from app.main import app
from app.repositories.order_status_history_sqlalchemy import (
    list_order_status_history,
)
from app.repositories.orders_sqlalchemy import (
    calculate_response_sla,
    create_order,
)
from app.schemas.order import OrderCreate, OrderSlaOutcome, OrderStatus
from app.schemas.property import PropertyType
from app.schemas.valuation import ValuationMethod
from app.services.order_processing_service import process_order
from engine.exceptions import ReferenceAreaNotFoundError
from engine.registry import ModelStatus, ModelVersionNotActiveError


client = TestClient(app)


def apartment_payload(external_order_id: str) -> dict[str, object]:
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


def test_persists_five_minute_response_deadline() -> None:
    response = client.post(
        "/orders",
        json=apartment_payload("SLA-DEADLINE-001"),
    )

    assert response.status_code == 201
    order = response.json()
    received_at = datetime.fromisoformat(order["received_at"])
    deadline_at = datetime.fromisoformat(order["response_deadline_at"])

    assert deadline_at - received_at == timedelta(seconds=300)
    assert order["responded_at"] is None
    assert order["sla_outcome"] == "PENDING"
    assert order["response_elapsed_seconds"] >= 0


@pytest.mark.parametrize(
    (
        "responded_delta",
        "observed_delta",
        "expected_elapsed",
        "expected_outcome",
    ),
    [
        (300.0, None, 300.0, OrderSlaOutcome.WITHIN_SLA),
        (None, 300.0, 300.0, OrderSlaOutcome.PENDING),
        (None, 300.001, 300.001, OrderSlaOutcome.BREACHED),
        (301.0, None, 301.0, OrderSlaOutcome.BREACHED),
        (None, -10.0, 0.0, OrderSlaOutcome.PENDING),
    ],
)
def test_calculates_sla_at_boundary_and_clamps_negative_elapsed(
    responded_delta: float | None,
    observed_delta: float | None,
    expected_elapsed: float,
    expected_outcome: OrderSlaOutcome,
) -> None:
    received_at = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
    deadline_at = received_at + timedelta(seconds=300)
    responded_at = (
        None
        if responded_delta is None
        else received_at + timedelta(seconds=responded_delta)
    )
    observed_at = (
        None
        if observed_delta is None
        else received_at + timedelta(seconds=observed_delta)
    )

    elapsed, outcome = calculate_response_sla(
        received_at=received_at,
        response_deadline_at=deadline_at,
        responded_at=responded_at,
        observed_at=observed_at,
    )

    assert elapsed == expected_elapsed
    assert outcome == expected_outcome


def test_processes_order_observed_exactly_at_deadline() -> None:
    received_at = datetime.now(timezone.utc) - timedelta(seconds=299)
    order_id = str(uuid4())

    with SessionLocal() as session:
        create_order(
            session=session,
            order=OrderCreate.model_validate(
                apartment_payload("PROCESS-EXACT-DEADLINE-001")
            ),
            internal_order_id=order_id,
            received_at=received_at,
        )
        result = process_order(
            session=session,
            internal_order_id=order_id,
            changed_by="sla-boundary-test",
            request_id="TRACE-EXACT-DEADLINE-001",
            observed_at=received_at + timedelta(seconds=300),
        )

    assert result is not None
    assert result.outcome == "COMPLETED"
    assert result.order.status == OrderStatus.COMPLETED
    assert result.order.sla_outcome == OrderSlaOutcome.WITHIN_SLA


def test_processes_order_once_and_preserves_idempotent_result() -> None:
    create_response = client.post(
        "/orders",
        json=apartment_payload("PROCESS-IDEMPOTENT-001"),
    )
    order_id = create_response.json()["internal_order_id"]

    first_response = client.post(
        f"/orders/{order_id}/process",
        headers={"X-Request-ID": "TRACE-PROCESS-001"},
    )
    second_response = client.post(
        f"/orders/{order_id}/process",
        headers={"X-Request-ID": "TRACE-PROCESS-RETRY-001"},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first = first_response.json()
    second = second_response.json()
    assert first["outcome"] == "COMPLETED"
    assert first["order"]["status"] == "COMPLETED"
    assert first["order"]["sla_outcome"] == "WITHIN_SLA"
    assert first["order"]["responded_at"] is not None
    assert first["contractual_delivery_enabled"] is False
    assert second["valuation"]["valuation_id"] == first["valuation"]["valuation_id"]

    with SessionLocal() as session:
        history = list_order_status_history(session, order_id)

    assert [(item.previous_status, item.new_status) for item in history] == [
        ("RECEIVED", "VALIDATING_INPUT"),
        ("VALIDATING_INPUT", "COMPLETED"),
    ]
    assert all(item.changed_by == "development-anonymous" for item in history)
    assert all(item.request_id == "TRACE-PROCESS-001" for item in history)
    assert history[0].reason_code == "AUTOMATIC_PROCESSING_STARTED"
    assert history[1].reason_code == "VALUATION_COMPLETED"


def test_processes_refusal_with_dossier_and_audit_context() -> None:
    payload = apartment_payload("PROCESS-REFUSAL-001")
    property_data = payload["property"]
    assert isinstance(property_data, dict)
    property_data.update(
        {
            "property_type": "HOUSE",
            "state": "RJ",
            "city": "Rio de Janeiro",
            "city_ibge_code": "3304557",
            "postal_code": "20010-000",
            "private_area_m2": 120,
            "built_area_m2": 140,
            "land_area_m2": 200,
        }
    )
    create_response = client.post("/orders", json=payload)
    order_id = create_response.json()["internal_order_id"]

    response = client.post(
        f"/orders/{order_id}/process",
        headers={"X-Request-ID": "TRACE-PROCESS-REFUSAL-001"},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["outcome"] == "REFUSED"
    assert result["order"]["status"] == "REFUSED"
    assert result["order"]["sla_outcome"] == "WITHIN_SLA"
    assert result["valuation"] is None
    assert result["refusal"]["reason_code"] == "TR_9_5_A"
    assert result["refusal"]["evidence"]["condition"] == (
        "MODEL_OR_DATASET_UNAVAILABLE"
    )

    with SessionLocal() as session:
        history = list_order_status_history(session, order_id)

    assert [item.reason_code for item in history] == [
        "AUTOMATIC_PROCESSING_STARTED",
        "TR_9_5_A",
    ]
    assert all(item.request_id == "TRACE-PROCESS-REFUSAL-001" for item in history)


def test_resumes_failed_order_through_queue_and_processing() -> None:
    create_response = client.post(
        "/orders",
        json=apartment_payload("PROCESS-RETRY-FAILED-001"),
    )
    order_id = create_response.json()["internal_order_id"]
    for next_status in (
        "VALIDATING_INPUT",
        "ACCEPTED",
        "QUEUED",
        "PROCESSING",
        "FAILED",
    ):
        response = client.patch(
            f"/orders/{order_id}/status",
            json={"status": next_status},
        )
        assert response.status_code == 200

    process_response = client.post(
        f"/orders/{order_id}/process",
        headers={"X-Request-ID": "TRACE-RETRY-FAILED-001"},
    )

    assert process_response.status_code == 200
    result = process_response.json()
    assert result["outcome"] == "COMPLETED"
    assert result["order"]["status"] == "COMPLETED"

    with SessionLocal() as session:
        history = list_order_status_history(session, order_id)

    assert [item.new_status for item in history[-3:]] == [
        "QUEUED",
        "PROCESSING",
        "COMPLETED",
    ]
    assert history[-3].reason_code == "AUTOMATIC_PROCESSING_STARTED"
    assert history[-2].reason_code == "AUTOMATIC_PROCESSING_STARTED"
    assert history[-1].reason_code == "VALUATION_COMPLETED"


def test_terminal_delivery_retry_reuses_persisted_valuation() -> None:
    create_response = client.post(
        "/orders",
        json=apartment_payload("PROCESS-DELIVERY-IDEMPOTENT-001"),
    )
    order_id = create_response.json()["internal_order_id"]
    completed_response = client.post(f"/orders/{order_id}/process")
    valuation_id = completed_response.json()["valuation"]["valuation_id"]

    delivery_response = client.patch(
        f"/orders/{order_id}/status",
        json={"status": "DELIVERING"},
    )
    retry_response = client.post(f"/orders/{order_id}/process")

    assert delivery_response.status_code == 200
    assert retry_response.status_code == 200
    assert retry_response.json()["outcome"] == "COMPLETED"
    assert retry_response.json()["valuation"]["valuation_id"] == valuation_id


def test_rejects_terminal_completed_order_without_valuation() -> None:
    create_response = client.post(
        "/orders",
        json=apartment_payload("PROCESS-CORRUPT-COMPLETED-001"),
    )
    order_id = create_response.json()["internal_order_id"]

    with SessionLocal() as session:
        order = session.get(OrderModel, order_id)
        assert order is not None
        order.status = "COMPLETED"
        order.responded_at = datetime.now(timezone.utc)
        session.commit()

    response = client.post(f"/orders/{order_id}/process")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ORDER_PROCESSING_STATE_INVALID"
    assert response.json()["detail"]["current_status"] == "COMPLETED"


def test_rejects_terminal_refused_order_without_refusal_dossier() -> None:
    create_response = client.post(
        "/orders",
        json=apartment_payload("PROCESS-CORRUPT-REFUSED-001"),
    )
    order_id = create_response.json()["internal_order_id"]

    with SessionLocal() as session:
        order = session.get(OrderModel, order_id)
        assert order is not None
        order.status = "REFUSED"
        order.responded_at = datetime.now(timezone.utc)
        session.commit()

    response = client.post(f"/orders/{order_id}/process")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ORDER_PROCESSING_STATE_INVALID"
    assert response.json()["detail"]["current_status"] == "REFUSED"


def test_accepts_legacy_naive_observation_timestamp_as_utc() -> None:
    order_id = str(uuid4())
    received_at = datetime.now(timezone.utc)

    with SessionLocal() as session:
        create_order(
            session=session,
            order=OrderCreate.model_validate(
                apartment_payload("PROCESS-NAIVE-TIMESTAMP-001")
            ),
            internal_order_id=order_id,
            received_at=received_at,
        )
        result = process_order(
            session=session,
            internal_order_id=order_id,
            changed_by="legacy-clock-test",
            request_id="TRACE-NAIVE-TIMESTAMP-001",
            observed_at=received_at.replace(tzinfo=None),
        )

    assert result is not None
    assert result.outcome == "COMPLETED"


def test_returns_none_if_order_disappears_after_valuation_attempt() -> None:
    order_id = str(uuid4())

    with SessionLocal() as session:
        create_order(
            session=session,
            order=OrderCreate.model_validate(
                apartment_payload("PROCESS-DISAPPEARS-001")
            ),
            internal_order_id=order_id,
            received_at=datetime.now(timezone.utc),
        )
        with (
            patch(
                "app.services.order_processing_service.calculate_and_store_valuation"
            ),
            patch(
                "app.services.order_processing_service.get_order_by_internal_id",
                return_value=None,
            ),
        ):
            result = process_order(
                session=session,
                internal_order_id=order_id,
                changed_by="concurrency-test",
                request_id="TRACE-DISAPPEARS-001",
            )

    assert result is None


@pytest.mark.parametrize("expired", [False, True])
def test_returns_none_if_status_update_loses_locked_order(expired: bool) -> None:
    order_id = str(uuid4())
    received_at = datetime.now(timezone.utc)
    if expired:
        received_at -= timedelta(seconds=301)

    with SessionLocal() as session:
        create_order(
            session=session,
            order=OrderCreate.model_validate(
                apartment_payload(f"PROCESS-STATUS-DISAPPEARS-{expired}")
            ),
            internal_order_id=order_id,
            received_at=received_at,
        )
        with patch(
            "app.services.order_processing_service.update_order_status_with_history",
            return_value=None,
        ):
            result = process_order(
                session=session,
                internal_order_id=order_id,
                changed_by="concurrency-test",
                request_id="TRACE-STATUS-DISAPPEARS-001",
            )

    assert result is None


def test_returns_not_found_when_processing_unknown_order() -> None:
    response = client.post("/orders/00000000-0000-0000-0000-000000000000/process")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ORDER_NOT_FOUND"


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_code"),
    [
        (
            InvalidOrderStatusTransitionError("RECEIVED", "COMPLETED"),
            409,
            "INVALID_STATUS_TRANSITION",
        ),
        (
            ModelVersionNotActiveError(
                ValuationMethod.RULE_BASED_V1,
                ModelStatus.DISABLED,
            ),
            503,
            "AVM_MODEL_NOT_ACTIVE",
        ),
        (
            ReferenceAreaNotFoundError(PropertyType.APARTMENT),
            422,
            "VALUATION_CALCULATION_ERROR",
        ),
    ],
)
def test_maps_expected_processing_failures_to_stable_http_errors(
    error: Exception,
    expected_status: int,
    expected_code: str,
) -> None:
    with patch("app.api.routes.valuations.process_order", side_effect=error):
        response = client.post(f"/orders/{uuid4()}/process")

    assert response.status_code == expected_status
    assert response.json()["detail"]["code"] == expected_code


def test_cancels_overdue_order_fail_closed_and_is_idempotent() -> None:
    create_response = client.post(
        "/orders",
        json=apartment_payload("PROCESS-TIMEOUT-001"),
    )
    order_id = create_response.json()["internal_order_id"]
    received_at = datetime.now(timezone.utc) - timedelta(seconds=301)

    with SessionLocal() as session:
        database_order = session.get(OrderModel, order_id)
        assert database_order is not None
        database_order.received_at = received_at
        database_order.response_deadline_at = received_at + timedelta(seconds=300)
        session.commit()

    first_response = client.post(
        f"/orders/{order_id}/process",
        headers={"X-Request-ID": "TRACE-TIMEOUT-001"},
    )
    second_response = client.post(f"/orders/{order_id}/process")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first = first_response.json()
    second = second_response.json()
    assert first["outcome"] == "CANCELLED"
    assert first["order"]["status"] == "CANCELLED"
    assert first["order"]["sla_outcome"] == "BREACHED"
    assert first["valuation"] is None
    assert first["refusal"] is None
    assert first["order"]["responded_at"] == second["order"]["responded_at"]

    with SessionLocal() as session:
        history = list_order_status_history(session, order_id)

    assert len(history) == 1
    assert history[0].new_status == "CANCELLED"
    assert history[0].changed_by == "development-anonymous"
    assert history[0].request_id == "TRACE-TIMEOUT-001"
    assert history[0].reason_code == "OS_TIMEOUT"
    assert history[0].context["maximum_response_seconds"] == 300


def test_generic_status_mutation_captures_actor_and_request_id() -> None:
    create_response = client.post(
        "/orders",
        json=apartment_payload("STATUS-AUDIT-CONTEXT-001"),
    )
    order_id = create_response.json()["internal_order_id"]

    update_response = client.patch(
        f"/orders/{order_id}/status",
        json={"status": "VALIDATING_INPUT"},
        headers={"X-Request-ID": "TRACE-STATUS-ACTOR-001"},
    )
    history_response = client.get(f"/orders/{order_id}/status-history")

    assert update_response.status_code == 200
    assert history_response.status_code == 200
    history = history_response.json()
    assert history[0]["changed_by"] == "development-anonymous"
    assert history[0]["request_id"] == "TRACE-STATUS-ACTOR-001"
    assert history[0]["reason_code"] == "CLIENT_STATUS_UPDATE"
    assert history[0]["context"] == {"endpoint": f"/orders/{order_id}/status"}


def test_history_model_rejects_update_and_delete() -> None:
    create_response = client.post(
        "/orders",
        json=apartment_payload("STATUS-APPEND-ONLY-001"),
    )
    order_id = create_response.json()["internal_order_id"]
    client.patch(
        f"/orders/{order_id}/status",
        json={"status": "VALIDATING_INPUT"},
    )

    with SessionLocal() as session:
        history = session.query(OrderStatusHistoryModel).one()
        history.reason_code = "TAMPERED"
        with pytest.raises(RuntimeError, match="append-only"):
            session.commit()
        session.rollback()

    with SessionLocal() as session:
        history = session.query(OrderStatusHistoryModel).one()
        session.delete(history)
        with pytest.raises(RuntimeError, match="append-only"):
            session.commit()
