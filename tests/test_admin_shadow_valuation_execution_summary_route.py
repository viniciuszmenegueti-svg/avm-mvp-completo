from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.domain.shadow_valuation_execution_model import (
    ShadowValuationExecutionModel,
)
from app.infrastructure.database import SessionLocal
from app.main import app


client = TestClient(app)

ADMIN_HEADERS = {"X-Admin-API-Key": "avm-test-admin-key"}


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
                requested_by="summary-route-test",
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
        "SHADOW-SUMMARY-ROUTE-001"
    )

    second_order_id = create_order(
        "SHADOW-SUMMARY-ROUTE-002"
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


def test_admin_gets_shadow_execution_summary() -> None:
    seed_summary_data()

    response = client.get(
        "/admin/shadow-valuation-executions/summary",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 3
    assert data["success"] == 2
    assert data["not_applicable"] == 1
    assert data["success_rate_percent"] == "66.67"
    assert data["distinct_orders"] == 2
    assert data["latest_execution_at"] is not None

    assert data["by_model_version"] == [
        {
            "model_version": "3.0.0",
            "total": 2,
        },
        {
            "model_version": None,
            "total": 1,
        },
    ]


def test_admin_filters_summary_by_period() -> None:
    seed_summary_data()

    response = client.get(
        "/admin/shadow-valuation-executions/summary",
        params={
            "executed_from": (
                "2026-08-02T00:00:00Z"
            ),
            "executed_until": (
                "2026-08-03T23:59:00Z"
            ),
        },
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 2
    assert data["success"] == 1
    assert data["not_applicable"] == 1
    assert data["success_rate_percent"] == "50.0"


def test_admin_summary_requires_api_key() -> None:
    response = client.get(
        "/admin/shadow-valuation-executions/summary"
    )

    assert response.status_code == 401


def test_admin_summary_rejects_invalid_api_key() -> None:
    response = client.get(
        "/admin/shadow-valuation-executions/summary",
        headers={
            "X-Admin-API-Key": "invalid-admin-key",
        },
    )

    assert response.status_code == 403


def test_admin_summary_rejects_invalid_period() -> None:
    response = client.get(
        "/admin/shadow-valuation-executions/summary",
        params={
            "executed_from": (
                "2026-08-05T00:00:00Z"
            ),
            "executed_until": (
                "2026-08-01T00:00:00Z"
            ),
        },
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 422

    detail = response.json()["detail"]

    assert detail["code"] == "INVALID_EXECUTION_PERIOD"


def test_summary_literal_is_not_treated_as_execution_id() -> None:
    response = client.get(
        "/admin/shadow-valuation-executions/summary",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
