from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.domain.shadow_valuation_execution_model import (
    ShadowValuationExecutionModel,
)
from app.domain.valuation_model import ValuationModel
from app.infrastructure.database import SessionLocal
from app.main import app
from app.repositories.orders_sqlalchemy import (
    get_order_by_internal_id,
)
from app.repositories.shadow_valuation_executions_sqlalchemy import (
    get_shadow_valuation_execution,
    list_shadow_valuation_executions_by_order,
)
from app.services.shadow_valuation_execution_audit_service import (
    ShadowExecutionResultStatus,
    record_not_applicable_shadow_execution,
    record_successful_shadow_execution,
)
from app.services.shadow_valuation_service import (
    calculate_shadow_valuation,
)


client = TestClient(app)


def apartment_payload(
    external_order_id: str,
    *,
    neighborhood: str = "Copacabana",
    postal_code: str = "22041-001",
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
    *,
    neighborhood: str = "Copacabana",
    postal_code: str = "22041-001",
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


def test_records_successful_shadow_execution() -> None:
    internal_order_id = create_order(
        "SHADOW-AUDIT-SUCCESS-001"
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
            requested_by="test-client",
            request_id="request-success-001",
        )

        execution_id = execution.execution_id

    with SessionLocal() as session:
        stored = get_shadow_valuation_execution(
            session,
            execution_id,
        )

        assert stored is not None
        assert stored.internal_order_id == internal_order_id
        assert stored.request_id == "request-success-001"
        assert stored.requested_by == "test-client"
        assert stored.result_status == (
            ShadowExecutionResultStatus.SUCCESS.value
        )
        assert stored.execution_mode == "SHADOW"
        assert stored.contractual_validity is False
        assert stored.formal_homologation is False
        assert stored.model_name == "RJ_FIXED_SPLIT_V3"
        assert stored.model_version == "3"
        assert stored.neighborhood == "Copacabana"
        assert stored.private_area_m2 is not None
        assert stored.estimated_value_brl is not None
        assert stored.confidence_lower_brl is not None
        assert stored.confidence_upper_brl is not None
        assert stored.price_per_m2_brl is not None
        assert stored.artifact_sha256 is not None
        assert len(stored.artifact_sha256) == 64
        assert stored.error_message is None
        assert stored.executed_at is not None

    assert shadow_execution_count() == 1
    assert official_valuation_count() == 0


def test_records_not_applicable_shadow_execution() -> None:
    internal_order_id = create_order(
        "SHADOW-AUDIT-NOT-APPLICABLE-001",
        neighborhood="Ipanema",
        postal_code="22420-000",
    )

    message = (
        "Bairro fora do dom?nio do modelo sombra: Ipanema."
    )

    with SessionLocal() as session:
        order = get_order_by_internal_id(
            session=session,
            internal_order_id=internal_order_id,
        )

        assert order is not None

        execution = (
            record_not_applicable_shadow_execution(
                session=session,
                internal_order_id=internal_order_id,
                property_data=order.property,
                requested_by="test-client",
                request_id="request-not-applicable-001",
                error_message=message,
            )
        )

        execution_id = execution.execution_id

    with SessionLocal() as session:
        stored = get_shadow_valuation_execution(
            session,
            execution_id,
        )

        assert stored is not None
        assert stored.result_status == (
            ShadowExecutionResultStatus.NOT_APPLICABLE.value
        )
        assert stored.execution_mode == "SHADOW"
        assert stored.contractual_validity is False
        assert stored.formal_homologation is False
        assert stored.neighborhood == "Ipanema"
        assert stored.error_message == message

        assert stored.model_name is None
        assert stored.model_version is None
        assert stored.estimated_value_brl is None
        assert stored.confidence_lower_brl is None
        assert stored.confidence_upper_brl is None
        assert stored.price_per_m2_brl is None
        assert stored.artifact_sha256 is None

    assert shadow_execution_count() == 1
    assert official_valuation_count() == 0


def test_allows_multiple_executions_for_same_order() -> None:
    internal_order_id = create_order(
        "SHADOW-AUDIT-MULTIPLE-001"
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

        first = record_successful_shadow_execution(
            session=session,
            internal_order_id=internal_order_id,
            property_data=order.property,
            result=result,
            requested_by="test-client",
            request_id="request-multiple-001",
        )

        second = record_successful_shadow_execution(
            session=session,
            internal_order_id=internal_order_id,
            property_data=order.property,
            result=result,
            requested_by="test-client",
            request_id="request-multiple-002",
        )

        assert first.execution_id != second.execution_id

    with SessionLocal() as session:
        executions = (
            list_shadow_valuation_executions_by_order(
                session,
                internal_order_id,
            )
        )

        assert len(executions) == 2
        assert {
            execution.request_id
            for execution in executions
        } == {
            "request-multiple-001",
            "request-multiple-002",
        }

    assert shadow_execution_count() == 2
    assert official_valuation_count() == 0


def test_lists_only_executions_from_requested_order() -> None:
    first_order_id = create_order(
        "SHADOW-AUDIT-LIST-001"
    )

    second_order_id = create_order(
        "SHADOW-AUDIT-LIST-002"
    )

    with SessionLocal() as session:
        first_order = get_order_by_internal_id(
            session=session,
            internal_order_id=first_order_id,
        )

        second_order = get_order_by_internal_id(
            session=session,
            internal_order_id=second_order_id,
        )

        assert first_order is not None
        assert second_order is not None

        first_result = calculate_shadow_valuation(
            first_order.property
        )

        second_result = calculate_shadow_valuation(
            second_order.property
        )

        record_successful_shadow_execution(
            session=session,
            internal_order_id=first_order_id,
            property_data=first_order.property,
            result=first_result,
            requested_by="test-client",
            request_id="request-list-first",
        )

        record_successful_shadow_execution(
            session=session,
            internal_order_id=second_order_id,
            property_data=second_order.property,
            result=second_result,
            requested_by="test-client",
            request_id="request-list-second",
        )

    with SessionLocal() as session:
        first_order_executions = (
            list_shadow_valuation_executions_by_order(
                session,
                first_order_id,
            )
        )

        assert len(first_order_executions) == 1
        assert (
            first_order_executions[0].internal_order_id
            == first_order_id
        )
        assert (
            first_order_executions[0].request_id
            == "request-list-first"
        )

    assert shadow_execution_count() == 2
    assert official_valuation_count() == 0


def test_truncates_not_applicable_error_message() -> None:
    internal_order_id = create_order(
        "SHADOW-AUDIT-ERROR-LIMIT-001",
        neighborhood="Ipanema",
        postal_code="22420-000",
    )

    long_message = "x" * 2500

    with SessionLocal() as session:
        order = get_order_by_internal_id(
            session=session,
            internal_order_id=internal_order_id,
        )

        assert order is not None

        execution = (
            record_not_applicable_shadow_execution(
                session=session,
                internal_order_id=internal_order_id,
                property_data=order.property,
                requested_by="test-client",
                request_id=None,
                error_message=long_message,
            )
        )

        execution_id = execution.execution_id

    with SessionLocal() as session:
        stored = get_shadow_valuation_execution(
            session,
            execution_id,
        )

        assert stored is not None
        assert stored.error_message is not None
        assert len(stored.error_message) == 2000
