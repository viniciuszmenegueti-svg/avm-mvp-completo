from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.domain.shadow_valuation_execution_model import (
    ShadowValuationExecutionModel,
)
from app.domain.valuation_model import ValuationModel
from app.infrastructure.database import SessionLocal
from app.main import app
from app.repositories.shadow_valuation_executions_sqlalchemy import (
    list_shadow_valuation_executions_by_order,
)


client = TestClient(app)


def apartment_payload(
    external_order_id: str,
    *,
    neighborhood: str,
    postal_code: str,
) -> dict[str, object]:
    return {
        "external_order_id": external_order_id,
        "property": {
            "property_type": "APARTMENT",
            "state": "RJ",
            "city": "Rio de Janeiro",
            "city_ibge_code": "3304557",
            "postal_code": postal_code,
            "neighborhood": neighborhood,
            "street": "Rua de Teste",
            "number": "100",
            "complement": "Apartamento 10",
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
    *,
    neighborhood: str,
    postal_code: str,
) -> str:
    response = client.post(
        "/orders",
        json=apartment_payload(
            external_order_id,
            neighborhood=neighborhood,
            postal_code=postal_code,
        ),
    )

    assert response.status_code == 201

    return response.json()["internal_order_id"]


def official_valuation_count() -> int:
    with SessionLocal() as session:
        statement = select(
            func.count(ValuationModel.valuation_id)
        )

        return int(session.scalar(statement) or 0)


def shadow_execution_count() -> int:
    with SessionLocal() as session:
        statement = select(
            func.count(
                ShadowValuationExecutionModel.execution_id
            )
        )

        return int(session.scalar(statement) or 0)


def test_route_records_successful_shadow_execution() -> None:
    internal_order_id = create_order(
        "SHADOW-ROUTE-AUDIT-SUCCESS-001",
        neighborhood="Copacabana",
        postal_code="22041-001",
    )

    response = client.get(
        f"/orders/{internal_order_id}/"
        "shadow-valuation-preview"
    )

    assert response.status_code == 200

    with SessionLocal() as session:
        executions = (
            list_shadow_valuation_executions_by_order(
                session,
                internal_order_id,
            )
        )

        assert len(executions) == 1

        execution = executions[0]

        assert execution.result_status == "SUCCESS"
        assert execution.execution_mode == "SHADOW"
        assert execution.contractual_validity is False
        assert execution.formal_homologation is False
        assert execution.model_name == "RJ_FIXED_SPLIT_V3"
        assert execution.model_version == "3"
        assert execution.neighborhood == "Copacabana"
        assert execution.estimated_value_brl is not None
        assert execution.artifact_sha256 is not None
        assert execution.error_message is None
        assert execution.request_id is not None
        assert execution.requested_by == (
            "development-anonymous"
        )

    assert shadow_execution_count() == 1
    assert official_valuation_count() == 0


def test_route_records_not_applicable_execution() -> None:
    internal_order_id = create_order(
        "SHADOW-ROUTE-AUDIT-NOT-APPLICABLE-001",
        neighborhood="Ipanema",
        postal_code="22420-000",
    )

    response = client.get(
        f"/orders/{internal_order_id}/"
        "shadow-valuation-preview"
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == (
        "SHADOW_VALUATION_NOT_APPLICABLE"
    )

    with SessionLocal() as session:
        executions = (
            list_shadow_valuation_executions_by_order(
                session,
                internal_order_id,
            )
        )

        assert len(executions) == 1

        execution = executions[0]

        assert execution.result_status == "NOT_APPLICABLE"
        assert execution.execution_mode == "SHADOW"
        assert execution.contractual_validity is False
        assert execution.formal_homologation is False
        assert execution.neighborhood == "Ipanema"
        assert execution.error_message is not None
        assert execution.model_name is None
        assert execution.estimated_value_brl is None

    assert shadow_execution_count() == 1
    assert official_valuation_count() == 0


def test_repeated_route_calls_create_distinct_audit_records() -> None:
    internal_order_id = create_order(
        "SHADOW-ROUTE-AUDIT-REPEATED-001",
        neighborhood="Botafogo",
        postal_code="22250-040",
    )

    endpoint = (
        f"/orders/{internal_order_id}/"
        "shadow-valuation-preview"
    )

    first_response = client.get(endpoint)
    second_response = client.get(endpoint)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == second_response.json()

    with SessionLocal() as session:
        executions = (
            list_shadow_valuation_executions_by_order(
                session,
                internal_order_id,
            )
        )

        assert len(executions) == 2
        assert (
            executions[0].execution_id
            != executions[1].execution_id
        )
        assert {
            execution.result_status
            for execution in executions
        } == {"SUCCESS"}

    assert shadow_execution_count() == 2
    assert official_valuation_count() == 0


def test_unknown_order_does_not_create_audit_record() -> None:
    internal_order_id = (
        "00000000-0000-0000-0000-000000000000"
    )

    response = client.get(
        f"/orders/{internal_order_id}/"
        "shadow-valuation-preview"
    )

    assert response.status_code == 404
    assert shadow_execution_count() == 0
    assert official_valuation_count() == 0
