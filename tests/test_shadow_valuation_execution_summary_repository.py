from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.domain.shadow_valuation_execution_model import (
    ShadowValuationExecutionModel,
)
from app.infrastructure.database import SessionLocal
from app.main import app
from app.repositories.shadow_valuation_executions_sqlalchemy import (
    summarize_shadow_valuation_executions,
)


client = TestClient(app)


def apartment_payload(
    external_order_id: str,
) -> dict[str, object]:
    return {
        "external_order_id": external_order_id,
        "property": {
            "property_type": "APARTMENT",
            "state": "RJ",
            "city": "Rio de Janeiro",
            "city_ibge_code": "3304557",
            "postal_code": "22041-001",
            "neighborhood": "Copacabana",
            "street": "Rua de Teste",
            "number": "100",
            "complement": "Apartamento 101",
            "private_area_m2": 90.0,
            "built_area_m2": 105.0,
            "land_area_m2": None,
            "bedrooms": 3,
            "bathrooms": 2,
            "parking_spaces": 1,
        },
    }


def create_order(
    external_order_id: str,
) -> str:
    response = client.post(
        "/orders",
        json=apartment_payload(external_order_id),
    )

    assert response.status_code == 201

    return response.json()["internal_order_id"]


def add_execution(
    *,
    internal_order_id: str,
    result_status: str,
    model_version: str | None,
    executed_at: datetime,
) -> None:
    with SessionLocal() as session:
        session.add(
            ShadowValuationExecutionModel(
                execution_id=str(uuid4()),
                internal_order_id=internal_order_id,
                request_id=str(uuid4()),
                requested_by="summary-test",
                result_status=result_status,
                model_name="rj-log-linear-shadow",
                model_version=model_version,
                execution_mode="SHADOW",
                contractual_validity=False,
                formal_homologation=False,
                neighborhood="Copacabana",
                executed_at=executed_at,
            )
        )
        session.commit()


def seed_summary_data() -> None:
    first_order_id = create_order(
        "SHADOW-SUMMARY-001"
    )

    second_order_id = create_order(
        "SHADOW-SUMMARY-002"
    )

    add_execution(
        internal_order_id=first_order_id,
        result_status="SUCCESS",
        model_version="3.0.0",
        executed_at=datetime(
            2026,
            8,
            1,
            10,
            0,
            tzinfo=timezone.utc,
        ),
    )

    add_execution(
        internal_order_id=first_order_id,
        result_status="NOT_APPLICABLE",
        model_version=None,
        executed_at=datetime(
            2026,
            8,
            2,
            10,
            0,
            tzinfo=timezone.utc,
        ),
    )

    add_execution(
        internal_order_id=second_order_id,
        result_status="SUCCESS",
        model_version="3.0.0",
        executed_at=datetime(
            2026,
            8,
            3,
            10,
            0,
            tzinfo=timezone.utc,
        ),
    )


def test_summarizes_shadow_executions() -> None:
    seed_summary_data()

    with SessionLocal() as session:
        summary = summarize_shadow_valuation_executions(
            session
        )

    assert summary["total"] == 3
    assert summary["success"] == 2
    assert summary["not_applicable"] == 1
    assert summary["success_rate_percent"] == 66.67
    assert summary["distinct_orders"] == 2
    assert summary["latest_execution_at"] is not None

    assert summary["by_model_version"] == [
        {
            "model_version": "3.0.0",
            "total": 2,
        },
        {
            "model_version": None,
            "total": 1,
        },
    ]


def test_summarizes_empty_history() -> None:
    with SessionLocal() as session:
        summary = summarize_shadow_valuation_executions(
            session
        )

    assert summary["total"] == 0
    assert summary["success"] == 0
    assert summary["not_applicable"] == 0
    assert summary["success_rate_percent"] == 0
    assert summary["distinct_orders"] == 0
    assert summary["latest_execution_at"] is None
    assert summary["by_model_version"] == []


def test_summarizes_execution_period() -> None:
    seed_summary_data()

    with SessionLocal() as session:
        summary = summarize_shadow_valuation_executions(
            session,
            executed_from=datetime(
                2026,
                8,
                2,
                0,
                0,
                tzinfo=timezone.utc,
            ),
            executed_until=datetime(
                2026,
                8,
                3,
                23,
                59,
                tzinfo=timezone.utc,
            ),
        )

    assert summary["total"] == 2
    assert summary["success"] == 1
    assert summary["not_applicable"] == 1
    assert summary["success_rate_percent"] == 50.0
