from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.domain.shadow_valuation_execution_model import (
    ShadowValuationExecutionModel,
)
from app.infrastructure.database import SessionLocal
from app.main import app
from app.repositories.shadow_valuation_executions_sqlalchemy import (
    search_shadow_valuation_executions,
)


client = TestClient(app)


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

    execution = ShadowValuationExecutionModel(
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

    with SessionLocal() as session:
        session.add(execution)
        session.commit()

    return execution_id


def seed_executions() -> tuple[str, str]:
    first_order_id = create_order(
        "SHADOW-SEARCH-001",
        "Copacabana",
    )

    second_order_id = create_order(
        "SHADOW-SEARCH-002",
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


def test_searches_all_executions_with_pagination() -> None:
    seed_executions()

    with SessionLocal() as session:
        items, total = search_shadow_valuation_executions(
            session,
            limit=2,
            offset=0,
        )

    assert total == 3
    assert len(items) == 2

    assert (
        items[0].executed_at
        >= items[1].executed_at
    )


def test_filters_by_status_and_requested_by() -> None:
    seed_executions()

    with SessionLocal() as session:
        items, total = search_shadow_valuation_executions(
            session,
            result_status="SUCCESS",
            requested_by="analyst-a",
            limit=100,
            offset=0,
        )

    assert total == 2
    assert len(items) == 2

    assert {
        execution.result_status
        for execution in items
    } == {"SUCCESS"}

    assert {
        execution.requested_by
        for execution in items
    } == {"analyst-a"}


def test_filters_by_order_and_neighborhood() -> None:
    first_order_id, _ = seed_executions()

    with SessionLocal() as session:
        items, total = search_shadow_valuation_executions(
            session,
            internal_order_id=first_order_id,
            neighborhood="Copacabana",
            limit=100,
            offset=0,
        )

    assert total == 2
    assert len(items) == 2

    assert {
        execution.internal_order_id
        for execution in items
    } == {first_order_id}


def test_filters_by_execution_period() -> None:
    seed_executions()

    with SessionLocal() as session:
        items, total = search_shadow_valuation_executions(
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
                2,
                23,
                59,
                tzinfo=timezone.utc,
            ),
            limit=100,
            offset=0,
        )

    assert total == 1
    assert len(items) == 1
    assert items[0].result_status == "NOT_APPLICABLE"


def test_filters_by_model_version() -> None:
    seed_executions()

    with SessionLocal() as session:
        items, total = search_shadow_valuation_executions(
            session,
            model_version="3.0.0",
            limit=100,
            offset=0,
        )

    assert total == 2
    assert len(items) == 2

    assert {
        execution.model_version
        for execution in items
    } == {"3.0.0"}
