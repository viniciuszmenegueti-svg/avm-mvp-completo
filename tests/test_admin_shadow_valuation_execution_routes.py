from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.infrastructure.database import SessionLocal
from app.main import app
from app.repositories.orders_sqlalchemy import get_order_by_internal_id
from app.services.shadow_valuation_execution_audit_service import (
    record_successful_shadow_execution,
)
from app.services.shadow_valuation_service import ShadowValuationResult
from engine.models.log_linear_shadow import ShadowModel, ShadowPrediction


def shadow_result() -> ShadowValuationResult:
    artifact_sha256 = "a" * 64
    return ShadowValuationResult(
        prediction=ShadowPrediction(
            estimated_value_brl=1_250_000.0,
            confidence_lower_brl=950_000.0,
            confidence_upper_brl=1_550_000.0,
            confidence_level=0.80,
            confidence_amplitude_percent=48.0,
            price_per_m2_brl=12_500.0,
            artifact_sha256=artifact_sha256,
            model_name="RJ_FIXED_SPLIT_V3",
            model_version="3",
            execution_mode="SHADOW",
            value_basis="MARKET_VALUE",
        ),
        model=ShadowModel(
            name="RJ_FIXED_SPLIT_V3",
            version="3",
            city_ibge_code="3304557",
            property_type="APARTMENT",
            supported_neighborhoods=("Copacabana", "Botafogo"),
            value_basis="MARKET_VALUE",
            artifact_sha256=artifact_sha256,
            coefficients=(1.0,),
            smearing_factor=1.0,
            interval_log_radius=0.25,
            input_domain={
                "private_area_m2": (20.0, 500.0),
                "bedrooms": (0.0, 10.0),
                "bathrooms": (1.0, 10.0),
                "parking_spaces": (0.0, 10.0),
            },
        ),
    )


client = TestClient(app)
ADMIN_HEADERS = {"X-Admin-API-Key": "avm-test-admin-key"}


def apartment_payload(external_order_id: str) -> dict[str, object]:
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


def create_order(external_order_id: str) -> str:
    response = client.post(
        "/orders",
        json=apartment_payload(external_order_id),
    )
    assert response.status_code == 201
    return response.json()["internal_order_id"]


def create_shadow_executions(internal_order_id: str, quantity: int) -> None:
    with SessionLocal() as session:
        order = get_order_by_internal_id(session, internal_order_id)
        assert order is not None
        result = shadow_result()

        for index in range(quantity):
            execution = record_successful_shadow_execution(
                session=session,
                internal_order_id=internal_order_id,
                property_data=order.property,
                result=result,
                requested_by="admin-history-test",
                request_id=f"admin-history-{index:03d}",
            )
            execution.executed_at = (
                datetime(2026, 1, 1, tzinfo=timezone.utc)
                + timedelta(seconds=index)
            )
            session.commit()


def history_url(internal_order_id: str) -> str:
    return (
        f"/admin/orders/{internal_order_id}/"
        "shadow-valuation-executions"
    )


def test_requires_admin_api_key() -> None:
    internal_order_id = create_order("SHADOW-HISTORY-ADMIN-001")

    response = client.get(history_url(internal_order_id))

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "ADMIN_API_KEY_REQUIRED"


def test_rejects_invalid_admin_api_key() -> None:
    internal_order_id = create_order("SHADOW-HISTORY-ADMIN-002")

    response = client.get(
        history_url(internal_order_id),
        headers={"X-Admin-API-Key": "invalid-key"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "INVALID_ADMIN_API_KEY"


def test_returns_404_for_unknown_order() -> None:
    internal_order_id = "00000000-0000-0000-0000-000000000999"

    response = client.get(
        history_url(internal_order_id),
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "ORDER_NOT_FOUND",
        "message": "Ordem de Serviço não encontrada.",
        "internal_order_id": internal_order_id,
    }


def test_returns_empty_history_for_existing_order() -> None:
    internal_order_id = create_order("SHADOW-HISTORY-ADMIN-003")

    response = client.get(
        history_url(internal_order_id),
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "internal_order_id": internal_order_id,
        "total": 0,
        "limit": 20,
        "offset": 0,
        "items": [],
    }


def test_returns_paginated_history_newest_first() -> None:
    internal_order_id = create_order("SHADOW-HISTORY-ADMIN-004")
    create_shadow_executions(internal_order_id, quantity=5)

    first_response = client.get(
        history_url(internal_order_id),
        headers=ADMIN_HEADERS,
        params={"limit": 2, "offset": 0},
    )
    second_response = client.get(
        history_url(internal_order_id),
        headers=ADMIN_HEADERS,
        params={"limit": 2, "offset": 2},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_page = first_response.json()
    second_page = second_response.json()

    assert first_page["total"] == 5
    assert first_page["limit"] == 2
    assert first_page["offset"] == 0
    assert len(first_page["items"]) == 2
    assert second_page["total"] == 5
    assert second_page["offset"] == 2
    assert len(second_page["items"]) == 2

    first_request_ids = [item["request_id"] for item in first_page["items"]]
    second_request_ids = [item["request_id"] for item in second_page["items"]]

    assert first_request_ids == ["admin-history-004", "admin-history-003"]
    assert second_request_ids == ["admin-history-002", "admin-history-001"]
    assert set(first_request_ids).isdisjoint(second_request_ids)

    for item in first_page["items"]:
        assert item["internal_order_id"] == internal_order_id
        assert item["result_status"] == "SUCCESS"
        assert item["execution_mode"] == "SHADOW"
        assert item["contractual_validity"] is False
        assert item["formal_homologation"] is False


def test_validates_pagination_parameters() -> None:
    internal_order_id = create_order("SHADOW-HISTORY-ADMIN-005")

    invalid_limit = client.get(
        history_url(internal_order_id),
        headers=ADMIN_HEADERS,
        params={"limit": 0},
    )
    excessive_limit = client.get(
        history_url(internal_order_id),
        headers=ADMIN_HEADERS,
        params={"limit": 101},
    )
    invalid_offset = client.get(
        history_url(internal_order_id),
        headers=ADMIN_HEADERS,
        params={"offset": -1},
    )

    assert invalid_limit.status_code == 422
    assert excessive_limit.status_code == 422
    assert invalid_offset.status_code == 422
