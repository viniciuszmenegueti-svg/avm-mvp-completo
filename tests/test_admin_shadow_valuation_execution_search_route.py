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
    neighborhood: str,
) -> dict[str, object]:
    return {
        "external_order_id": external_order_id,
        "property": {
            "property_type": "APARTMENT",
            "state": "RJ",
            "city": "Rio de Janeiro",
            "city_ibge_code": "3304557",
            "postal_code": "22041-001",
            "neighborhood": neighborhood,
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
    neighborhood: str,
) -> str:
    response = client.post(
        "/orders",
        json=apartment_payload(
            external_order_id,
            neighborhood,
        ),
    )

    assert response.status_code == 201

    return response.json()["internal_order_id"]


def add_execution(
    *,
    internal_order_id: str,
    result_status: str,
    requested_by: str,
    model_version: str | None,
    neighborhood: str,
    executed_at: datetime,
) -> str:
    execution_id = str(uuid4())

    with SessionLocal() as session:
        session.add(
            ShadowValuationExecutionModel(
                execution_id=execution_id,
                internal_order_id=internal_order_id,
                request_id=f"request-{execution_id}",
                requested_by=requested_by,
                result_status=result_status,
                model_name="rj-log-linear-shadow",
                model_version=model_version,
                execution_mode="SHADOW",
                contractual_validity=False,
                formal_homologation=False,
                neighborhood=neighborhood,
                executed_at=executed_at,
            )
        )
        session.commit()

    return execution_id


def seed_executions() -> tuple[str, str]:
    first_order_id = create_order(
        "SHADOW-SEARCH-ROUTE-001",
        "Copacabana",
    )

    second_order_id = create_order(
        "SHADOW-SEARCH-ROUTE-002",
        "Botafogo",
    )

    add_execution(
        internal_order_id=first_order_id,
        result_status="SUCCESS",
        requested_by="analyst-a",
        model_version="3.0.0",
        neighborhood="Copacabana",
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
        requested_by="analyst-b",
        model_version=None,
        neighborhood="Copacabana",
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
        requested_by="analyst-a",
        model_version="3.0.0",
        neighborhood="Botafogo",
        executed_at=datetime(
            2026,
            8,
            3,
            10,
            0,
            tzinfo=timezone.utc,
        ),
    )

    return first_order_id, second_order_id


def test_admin_searches_shadow_executions() -> None:
    seed_executions()

    response = client.get(
        "/admin/shadow-valuation-executions",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 3
    assert data["limit"] == 20
    assert data["offset"] == 0
    assert len(data["items"]) == 3


def test_admin_filters_shadow_executions() -> None:
    seed_executions()

    response = client.get(
        "/admin/shadow-valuation-executions",
        params={
            "result_status": "SUCCESS",
            "requested_by": "analyst-a",
            "model_version": "3.0.0",
        },
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 2

    assert {
        item["result_status"]
        for item in data["items"]
    } == {"SUCCESS"}


def test_admin_paginates_shadow_executions() -> None:
    seed_executions()

    response = client.get(
        "/admin/shadow-valuation-executions",
        params={
            "limit": 1,
            "offset": 1,
        },
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 3
    assert data["limit"] == 1
    assert data["offset"] == 1
    assert len(data["items"]) == 1


def test_admin_search_requires_api_key() -> None:
    response = client.get(
        "/admin/shadow-valuation-executions"
    )

    assert response.status_code == 401


def test_admin_search_rejects_invalid_api_key() -> None:
    response = client.get(
        "/admin/shadow-valuation-executions",
        headers={
            "X-Admin-API-Key": "invalid-admin-key",
        },
    )

    assert response.status_code == 403


def test_admin_search_rejects_invalid_period() -> None:
    response = client.get(
        "/admin/shadow-valuation-executions",
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


def test_literal_search_route_is_not_treated_as_execution_id() -> None:
    response = client.get(
        "/admin/shadow-valuation-executions",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
