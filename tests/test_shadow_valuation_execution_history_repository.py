from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.infrastructure.database import SessionLocal
from app.main import app
from app.repositories.orders_sqlalchemy import (
    get_order_by_internal_id,
)
from app.repositories.shadow_valuation_executions_sqlalchemy import (
    list_paginated_shadow_valuation_executions_by_order,
)
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


def create_order(
    external_order_id: str,
) -> str:
    response = client.post(
        "/orders",
        json=apartment_payload(external_order_id),
    )

    assert response.status_code == 201

    return response.json()["internal_order_id"]


def create_shadow_executions(
    internal_order_id: str,
    quantity: int,
) -> None:
    with SessionLocal() as session:
        order = get_order_by_internal_id(
            session=session,
            internal_order_id=internal_order_id,
        )

        assert order is not None

        result = shadow_result()

        for index in range(quantity):
            execution = record_successful_shadow_execution(
                session=session,
                internal_order_id=internal_order_id,
                property_data=order.property,
                result=result,
                requested_by="history-test",
                request_id=f"history-request-{index:03d}",
            )
            execution.executed_at = (
                datetime(2026, 1, 1, tzinfo=timezone.utc)
                + timedelta(seconds=index)
            )
            session.commit()


def test_lists_paginated_shadow_execution_history() -> None:
    internal_order_id = create_order(
        "SHADOW-HISTORY-REPOSITORY-001"
    )

    create_shadow_executions(
        internal_order_id,
        quantity=5,
    )

    with SessionLocal() as session:
        first_page, first_total = (
            list_paginated_shadow_valuation_executions_by_order(
                session,
                internal_order_id,
                limit=2,
                offset=0,
            )
        )

        second_page, second_total = (
            list_paginated_shadow_valuation_executions_by_order(
                session,
                internal_order_id,
                limit=2,
                offset=2,
            )
        )

    assert first_total == 5
    assert second_total == 5
    assert len(first_page) == 2
    assert len(second_page) == 2

    first_ids = {
        execution.execution_id
        for execution in first_page
    }

    second_ids = {
        execution.execution_id
        for execution in second_page
    }

    assert first_ids.isdisjoint(second_ids)


def test_returns_empty_page_for_order_without_executions() -> None:
    internal_order_id = create_order(
        "SHADOW-HISTORY-REPOSITORY-002"
    )

    with SessionLocal() as session:
        items, total = (
            list_paginated_shadow_valuation_executions_by_order(
                session,
                internal_order_id,
                limit=20,
                offset=0,
            )
        )

    assert total == 0
    assert items == []


def test_history_is_isolated_by_order() -> None:
    first_order_id = create_order(
        "SHADOW-HISTORY-REPOSITORY-003"
    )

    second_order_id = create_order(
        "SHADOW-HISTORY-REPOSITORY-004"
    )

    create_shadow_executions(
        first_order_id,
        quantity=3,
    )

    create_shadow_executions(
        second_order_id,
        quantity=1,
    )

    with SessionLocal() as session:
        first_items, first_total = (
            list_paginated_shadow_valuation_executions_by_order(
                session,
                first_order_id,
                limit=100,
                offset=0,
            )
        )

    assert first_total == 3
    assert len(first_items) == 3
    assert {
        execution.internal_order_id
        for execution in first_items
    } == {first_order_id}
