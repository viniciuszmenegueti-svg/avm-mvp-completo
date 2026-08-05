from fastapi.testclient import TestClient

from app.infrastructure.database import SessionLocal
from app.main import app
from app.repositories.orders_sqlalchemy import (
    get_order_by_internal_id,
)
from app.services.shadow_valuation_execution_audit_service import (
    record_successful_shadow_execution,
)
from app.services.shadow_valuation_service import (
    calculate_shadow_valuation,
)


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
            "street": "Rua Barata Ribeiro",
            "number": "500",
            "complement": "Apartamento 801",
            "private_area_m2": 100.0,
            "built_area_m2": 115.0,
            "land_area_m2": None,
            "bedrooms": 3,
            "bathrooms": 2,
            "parking_spaces": 1,
        },
    }


def create_execution() -> tuple[str, str]:
    response = client.post(
        "/orders",
        json=apartment_payload(
            "SHADOW-EXECUTION-DETAIL-001"
        ),
    )

    assert response.status_code == 201

    internal_order_id = (
        response.json()["internal_order_id"]
    )

    with SessionLocal() as session:
        order = get_order_by_internal_id(
            session=session,
            internal_order_id=internal_order_id,
        )

        assert order is not None

        result = calculate_shadow_valuation(
            order.property
        )

        execution = record_successful_shadow_execution(
            session=session,
            internal_order_id=internal_order_id,
            property_data=order.property,
            result=result,
            requested_by="detail-test",
            request_id="detail-request-001",
        )

        return (
            internal_order_id,
            execution.execution_id,
        )


def test_admin_gets_shadow_execution_detail() -> None:
    internal_order_id, execution_id = create_execution()

    response = client.get(
        (
            "/admin/shadow-valuation-executions/"
            f"{execution_id}"
        ),
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["execution_id"] == execution_id
    assert data["internal_order_id"] == internal_order_id
    assert data["result_status"] == "SUCCESS"
    assert data["requested_by"] == "detail-test"
    assert data["request_id"] == "detail-request-001"
    assert data["contractual_validity"] is False
    assert data["formal_homologation"] is False


def test_shadow_execution_detail_requires_admin_key() -> None:
    _, execution_id = create_execution()

    response = client.get(
        (
            "/admin/shadow-valuation-executions/"
            f"{execution_id}"
        )
    )

    assert response.status_code == 401


def test_shadow_execution_detail_rejects_invalid_key() -> None:
    _, execution_id = create_execution()

    response = client.get(
        (
            "/admin/shadow-valuation-executions/"
            f"{execution_id}"
        ),
        headers={
            "X-Admin-API-Key": "invalid-admin-key",
        },
    )

    assert response.status_code == 403


def test_shadow_execution_detail_returns_404() -> None:
    response = client.get(
        (
            "/admin/shadow-valuation-executions/"
            "00000000-0000-0000-0000-000000000000"
        ),
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 404

    detail = response.json()["detail"]

    assert (
        detail["code"]
        == "SHADOW_EXECUTION_NOT_FOUND"
    )
