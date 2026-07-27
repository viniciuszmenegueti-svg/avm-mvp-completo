import pytest

from fastapi.testclient import TestClient

from app.main import app
from app.repositories.orders_memory import (
    external_order_index,
    orders_storage,
)


client = TestClient(app)


def setup_function() -> None:
    orders_storage.clear()
    external_order_index.clear()


def apartment_payload(
    external_order_id: str = "CX-2026-000001",
) -> dict:
    return {
        "external_order_id": external_order_id,
        "property": {
            "property_type": "APARTMENT",
            "state": "SP",
            "city": "São Paulo",
            "city_ibge_code": "3550308",
            "postal_code": "29060-000",
            "neighborhood": "Jardim da Penha",
            "street": "Avenida Fernando Ferrari",
            "number": "100",
            "complement": "Apartamento 302",
            "private_area_m2": 72.5,
            "built_area_m2": 85.0,
            "land_area_m2": None,
            "bedrooms": 3,
            "bathrooms": 2,
            "parking_spaces": 1,
        },
    }


def test_create_order() -> None:
    response = client.post(
        "/orders",
        json=apartment_payload(),
    )

    assert response.status_code == 201

    body = response.json()

    assert body["external_order_id"] == "CX-2026-000001"
    assert body["status"] == "RECEIVED"
    assert body["internal_order_id"]
    assert body["received_at"]


def test_get_order() -> None:
    create_response = client.post(
        "/orders",
        json=apartment_payload(),
    )

    internal_order_id = create_response.json()["internal_order_id"]

    get_response = client.get(f"/orders/{internal_order_id}")

    assert get_response.status_code == 200
    assert get_response.json()["internal_order_id"] == internal_order_id


def test_get_order_not_found() -> None:
    response = client.get(
        "/orders/00000000-0000-0000-0000-000000000000",
    )

    assert response.status_code == 404


def test_get_order_with_invalid_id() -> None:
    response = client.get("/orders/identificador-invalido")

    assert response.status_code == 422


def test_duplicate_external_order_id() -> None:
    first_response = client.post(
        "/orders",
        json=apartment_payload(),
    )

    second_response = client.post(
        "/orders",
        json=apartment_payload(),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409

    first_internal_id = first_response.json()["internal_order_id"]

    detail = second_response.json()["detail"]

    assert detail["external_order_id"] == "CX-2026-000001"
    assert detail["internal_order_id"] == first_internal_id


def test_different_external_ids_are_allowed() -> None:
    first_response = client.post(
        "/orders",
        json=apartment_payload("CX-2026-000001"),
    )

    second_response = client.post(
        "/orders",
        json=apartment_payload("CX-2026-000002"),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    assert (
        first_response.json()["internal_order_id"]
        != second_response.json()["internal_order_id"]
    )


def test_rejects_order_from_unsupported_city() -> None:
    payload = apartment_payload("UNSUPPORTED-CITY-001")

    payload["property"]["state"] = "ES"
    payload["property"]["city"] = "Vitória"
    payload["property"]["city_ibge_code"] = "3205309"

    response = client.post(
        "/orders",
        json=payload,
    )

    assert response.status_code == 422

    detail = response.json()["detail"]

    assert detail == {
        "code": "UNSUPPORTED_CITY",
        "message": (
            "A cidade informada não está habilitada para processamento de AVM."
        ),
        "city_ibge_code": "3205309",
    }


def test_refuses_order_when_city_does_not_match_ibge_code() -> None:
    payload = apartment_payload("CITY-MISMATCH-001")

    payload["property"]["state"] = "RJ"
    payload["property"]["city"] = "Rio de Janeiro"
    payload["property"]["city_ibge_code"] = "3550308"

    response = client.post(
        "/orders",
        json=payload,
    )

    assert response.status_code == 201

    response_body = response.json()

    assert response_body["external_order_id"] == "CITY-MISMATCH-001"
    assert response_body["status"] == "REFUSED"

    internal_order_id = response_body["internal_order_id"]

    refusal_response = client.get(
        f"/orders/{internal_order_id}/refusal",
    )

    assert refusal_response.status_code == 200

    refusal = refusal_response.json()

    assert refusal["reason_code"] == "TR_9_5_B"
    assert refusal["contract_reference"] == "TR §9.5(b) e §9.6"
    assert refusal["evidence"] == {
        "condition": "CITY_DATA_MISMATCH",
        "city_ibge_code": "3550308",
        "informed_city": "Rio de Janeiro",
        "informed_state": "RJ",
        "expected_city": "São Paulo",
        "expected_state": "SP",
    }


def test_refuses_order_when_conflict_of_interest_is_declared() -> None:
    payload = apartment_payload("CONFLICT-OF-INTEREST-001")

    payload["conflict_of_interest"] = {
        "has_conflict": True,
        "conflict_type": "RELATED_PARTY",
        "description": ("Solicitante possui vínculo com o responsável pela avaliação."),
        "identified_by": "COMPLIANCE",
    }

    response = client.post(
        "/orders",
        json=payload,
    )

    assert response.status_code == 201

    response_body = response.json()

    assert response_body["external_order_id"] == "CONFLICT-OF-INTEREST-001"
    assert response_body["status"] == "REFUSED"

    internal_order_id = response_body["internal_order_id"]

    refusal_response = client.get(
        f"/orders/{internal_order_id}/refusal",
    )

    assert refusal_response.status_code == 200

    refusal = refusal_response.json()

    assert refusal["reason_code"] == "TR_9_5_C"
    assert refusal["contract_reference"] == "TR §9.5(c) e §9.6"
    assert refusal["evidence"] == {
        "condition": "CONFLICT_OF_INTEREST_DECLARED",
        "conflict_type": "RELATED_PARTY",
        "description": ("Solicitante possui vínculo com o responsável pela avaliação."),
        "identified_by": "COMPLIANCE",
    }


def test_refuses_order_when_location_is_not_confirmed() -> None:
    payload = apartment_payload("LOCATION-NOT-CONFIRMED-001")

    payload["location_confirmation"] = {
        "is_confirmed": False,
        "confirmation_method": "DOCUMENT_VALIDATION",
        "evidence_reference": "MATRICULA-NAO-LOCALIZADA",
        "failure_reason": (
            "O endereço informado não pôde ser confirmado pelas evidências disponíveis."
        ),
        "verified_by": "VALIDATION_PIPELINE",
    }

    response = client.post(
        "/orders",
        json=payload,
    )

    assert response.status_code == 201

    response_body = response.json()

    assert response_body["external_order_id"] == "LOCATION-NOT-CONFIRMED-001"
    assert response_body["status"] == "REFUSED"

    internal_order_id = response_body["internal_order_id"]

    refusal_response = client.get(
        f"/orders/{internal_order_id}/refusal",
    )

    assert refusal_response.status_code == 200

    refusal = refusal_response.json()

    assert refusal["reason_code"] == "TR_9_5_D"
    assert refusal["contract_reference"] == "TR §9.5(d) e §9.6"
    assert refusal["evidence"] == {
        "condition": "LOCATION_NOT_CONFIRMED",
        "confirmation_method": "DOCUMENT_VALIDATION",
        "evidence_reference": "MATRICULA-NAO-LOCALIZADA",
        "failure_reason": (
            "O endereço informado não pôde ser confirmado pelas evidências disponíveis."
        ),
        "verified_by": "VALIDATION_PIPELINE",
    }


def test_list_orders_when_database_is_empty() -> None:
    response = client.get("/orders")

    assert response.status_code == 200

    assert response.json() == {
        "total": 0,
        "limit": 20,
        "offset": 0,
        "items": [],
    }


def test_list_orders() -> None:
    client.post(
        "/orders",
        json=apartment_payload("LIST-ORDER-001"),
    )
    client.post(
        "/orders",
        json=apartment_payload("LIST-ORDER-002"),
    )

    response = client.get("/orders")

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 2
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert len(body["items"]) == 2

    returned_external_ids = {item["external_order_id"] for item in body["items"]}

    assert returned_external_ids == {
        "LIST-ORDER-001",
        "LIST-ORDER-002",
    }


def test_list_orders_with_pagination() -> None:
    for order_number in range(1, 4):
        response = client.post(
            "/orders",
            json=apartment_payload(
                f"PAGINATION-{order_number:03d}",
            ),
        )

        assert response.status_code == 201

    response = client.get(
        "/orders",
        params={
            "limit": 1,
            "offset": 1,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 3
    assert body["limit"] == 1
    assert body["offset"] == 1
    assert len(body["items"]) == 1


def test_list_orders_filtered_by_status() -> None:
    client.post(
        "/orders",
        json=apartment_payload("STATUS-FILTER-001"),
    )
    client.post(
        "/orders",
        json=apartment_payload("STATUS-FILTER-002"),
    )

    response = client.get(
        "/orders",
        params={
            "order_status": "RECEIVED",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 2
    assert len(body["items"]) == 2

    assert all(item["status"] == "RECEIVED" for item in body["items"])


def test_list_orders_filtered_by_status_without_results() -> None:
    client.post(
        "/orders",
        json=apartment_payload("STATUS-EMPTY-001"),
    )

    response = client.get(
        "/orders",
        params={
            "order_status": "COMPLETED",
        },
    )

    assert response.status_code == 200

    assert response.json() == {
        "total": 0,
        "limit": 20,
        "offset": 0,
        "items": [],
    }


def test_list_orders_rejects_invalid_status() -> None:
    response = client.get(
        "/orders",
        params={
            "order_status": "INVALID_STATUS",
        },
    )

    assert response.status_code == 422


def test_updates_order_status() -> None:
    create_response = client.post(
        "/orders",
        json=apartment_payload("STATUS-ENDPOINT-001"),
    )

    internal_order_id = create_response.json()["internal_order_id"]

    update_response = client.patch(
        f"/orders/{internal_order_id}/status",
        json={
            "status": "VALIDATING_INPUT",
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["status"] == "VALIDATING_INPUT"

    get_response = client.get(f"/orders/{internal_order_id}")

    assert get_response.status_code == 200
    assert get_response.json()["status"] == "VALIDATING_INPUT"


def test_rejects_invalid_order_status_transition() -> None:
    create_response = client.post(
        "/orders",
        json=apartment_payload("STATUS-ENDPOINT-002"),
    )

    internal_order_id = create_response.json()["internal_order_id"]

    response = client.patch(
        f"/orders/{internal_order_id}/status",
        json={
            "status": "COMPLETED",
        },
    )

    assert response.status_code == 409

    assert response.json()["detail"] == {
        "code": "INVALID_STATUS_TRANSITION",
        "message": ("A transição de RECEIVED para COMPLETED não é permitida."),
        "current_status": "RECEIVED",
        "new_status": "COMPLETED",
    }


def test_rejects_refused_status_through_generic_endpoint() -> None:
    create_response = client.post(
        "/orders",
        json=apartment_payload("STATUS-ENDPOINT-REFUSED-001"),
    )

    assert create_response.status_code == 201

    internal_order_id = create_response.json()["internal_order_id"]

    validating_response = client.patch(
        f"/orders/{internal_order_id}/status",
        json={
            "status": "VALIDATING_INPUT",
        },
    )

    assert validating_response.status_code == 200

    refused_response = client.patch(
        f"/orders/{internal_order_id}/status",
        json={
            "status": "REFUSED",
        },
    )

    assert refused_response.status_code == 409

    assert refused_response.json()["detail"] == {
        "code": "REFUSAL_REQUIRES_DOSSIER",
        "message": (
            "O status REFUSED não pode ser aplicado pelo endpoint genérico. "
            "A recusa deve ser registrada por um serviço contratual com dossiê."
        ),
        "new_status": "REFUSED",
    }


def test_update_status_returns_not_found() -> None:
    internal_order_id = "00000000-0000-0000-0000-000000000000"

    response = client.patch(
        f"/orders/{internal_order_id}/status",
        json={
            "status": "VALIDATING_INPUT",
        },
    )

    assert response.status_code == 404

    assert response.json()["detail"]["code"] == "ORDER_NOT_FOUND"


def test_status_update_creates_history() -> None:
    from app.infrastructure.database import SessionLocal
    from app.repositories.order_status_history_sqlalchemy import (
        list_order_status_history,
    )

    create_response = client.post(
        "/orders",
        json=apartment_payload("STATUS-HISTORY-001"),
    )

    assert create_response.status_code == 201

    internal_order_id = create_response.json()["internal_order_id"]

    update_response = client.patch(
        f"/orders/{internal_order_id}/status",
        json={
            "status": "VALIDATING_INPUT",
        },
    )

    assert update_response.status_code == 200

    with SessionLocal() as session:
        history = list_order_status_history(
            session=session,
            internal_order_id=internal_order_id,
        )

    assert len(history) == 1
    assert history[0].previous_status == "RECEIVED"
    assert history[0].new_status == "VALIDATING_INPUT"
    assert history[0].changed_at is not None


def test_get_order_status_history() -> None:
    create_response = client.post(
        "/orders",
        json=apartment_payload("GET-HISTORY-001"),
    )

    assert create_response.status_code == 201

    internal_order_id = create_response.json()["internal_order_id"]

    first_update = client.patch(
        f"/orders/{internal_order_id}/status",
        json={
            "status": "VALIDATING_INPUT",
        },
    )

    assert first_update.status_code == 200

    second_update = client.patch(
        f"/orders/{internal_order_id}/status",
        json={
            "status": "COMPLETED",
        },
    )

    assert second_update.status_code == 200

    response = client.get(
        f"/orders/{internal_order_id}/status-history",
    )

    assert response.status_code == 200

    history = response.json()

    assert len(history) == 2

    assert history[0]["previous_status"] == "RECEIVED"
    assert history[0]["new_status"] == "VALIDATING_INPUT"

    assert history[1]["previous_status"] == "VALIDATING_INPUT"
    assert history[1]["new_status"] == "COMPLETED"

    assert history[0]["internal_order_id"] == internal_order_id
    assert history[0]["changed_at"]


def test_get_empty_order_status_history() -> None:
    create_response = client.post(
        "/orders",
        json=apartment_payload("GET-HISTORY-EMPTY-001"),
    )

    internal_order_id = create_response.json()["internal_order_id"]

    response = client.get(
        f"/orders/{internal_order_id}/status-history",
    )

    assert response.status_code == 200
    assert response.json() == []


def test_get_status_history_returns_not_found() -> None:
    internal_order_id = "00000000-0000-0000-0000-000000000000"

    response = client.get(
        f"/orders/{internal_order_id}/status-history",
    )

    assert response.status_code == 404

    assert response.json()["detail"]["code"] == "ORDER_NOT_FOUND"


def test_get_status_history_rejects_invalid_order_id() -> None:
    response = client.get(
        "/orders/identificador-invalido/status-history",
    )

    assert response.status_code == 422


def test_status_update_rolls_back_when_history_fails(
    monkeypatch,
) -> None:
    from app.services import (
        order_status_update as status_update_service,
    )

    create_response = client.post(
        "/orders",
        json=apartment_payload("STATUS-ROLLBACK-001"),
    )

    assert create_response.status_code == 201

    internal_order_id = create_response.json()["internal_order_id"]

    def fail_history_creation(*args, **kwargs):
        raise RuntimeError(
            "Falha simulada ao gravar histórico",
        )

    monkeypatch.setattr(
        status_update_service,
        "create_order_status_history",
        fail_history_creation,
    )

    with pytest.raises(RuntimeError):
        client.patch(
            f"/orders/{internal_order_id}/status",
            json={
                "status": "VALIDATING_INPUT",
            },
        )

    get_response = client.get(f"/orders/{internal_order_id}")

    assert get_response.status_code == 200
    assert get_response.json()["status"] == "RECEIVED"


def test_get_order_by_external_id() -> None:
    external_order_id = "EXTERNAL-LOOKUP-001"

    create_response = client.post(
        "/orders",
        json=apartment_payload(external_order_id),
    )

    assert create_response.status_code == 201

    response = client.get(
        f"/orders/external/{external_order_id}",
    )

    assert response.status_code == 200

    body = response.json()

    assert body["external_order_id"] == external_order_id
    assert body["internal_order_id"] == create_response.json()["internal_order_id"]
    assert body["status"] == "RECEIVED"


def test_get_order_by_external_id_returns_not_found() -> None:
    response = client.get(
        "/orders/external/EXTERNAL-NOT-FOUND",
    )

    assert response.status_code == 404

    assert response.json()["detail"] == {
        "code": "ORDER_NOT_FOUND",
        "message": "Ordem de Serviço não encontrada.",
        "external_order_id": "EXTERNAL-NOT-FOUND",
    }


def test_rolls_back_entire_conflict_refusal_when_service_fails(
    monkeypatch,
) -> None:
    from uuid import UUID

    from app.api.routes import orders as order_routes
    from app.infrastructure.database import SessionLocal
    from app.repositories.order_refusals_sqlalchemy import (
        get_order_refusal_by_internal_order_id,
    )
    from app.repositories.order_status_history_sqlalchemy import (
        list_order_status_history,
    )
    from app.repositories.orders_sqlalchemy import get_order_by_internal_id

    internal_order_id = "00000000-0000-0000-0000-000000000101"
    payload = apartment_payload("ATOMIC-CONFLICT-ROLLBACK-001")
    payload["conflict_of_interest"] = {
        "has_conflict": True,
        "conflict_type": "RELATED_PARTY",
        "description": "Falha simulada durante o registro da recusa.",
        "identified_by": "COMPLIANCE",
    }

    monkeypatch.setattr(
        order_routes,
        "uuid4",
        lambda: UUID(internal_order_id),
    )

    def fail_refusal(*args, **kwargs):
        raise RuntimeError("falha simulada na recusa por conflito")

    monkeypatch.setattr(
        order_routes,
        "refuse_order_for_conflict_of_interest",
        fail_refusal,
    )

    with pytest.raises(
        RuntimeError,
        match="falha simulada na recusa por conflito",
    ):
        client.post(
            "/orders",
            json=payload,
        )

    with SessionLocal() as session:
        stored_order = get_order_by_internal_id(
            session=session,
            internal_order_id=internal_order_id,
        )
        stored_refusal = get_order_refusal_by_internal_order_id(
            session=session,
            internal_order_id=internal_order_id,
        )
        history = list_order_status_history(
            session=session,
            internal_order_id=internal_order_id,
        )

    assert stored_order is None
    assert stored_refusal is None
    assert history == []


def test_rolls_back_entire_location_refusal_when_service_fails(
    monkeypatch,
) -> None:
    from uuid import UUID

    from app.api.routes import orders as order_routes
    from app.infrastructure.database import SessionLocal
    from app.repositories.order_refusals_sqlalchemy import (
        get_order_refusal_by_internal_order_id,
    )
    from app.repositories.order_status_history_sqlalchemy import (
        list_order_status_history,
    )
    from app.repositories.orders_sqlalchemy import get_order_by_internal_id

    internal_order_id = "00000000-0000-0000-0000-000000000102"
    payload = apartment_payload("ATOMIC-LOCATION-ROLLBACK-001")
    payload["location_confirmation"] = {
        "is_confirmed": False,
        "confirmation_method": "DOCUMENT_VALIDATION",
        "evidence_reference": "MATRICULA-NAO-LOCALIZADA",
        "failure_reason": "Falha simulada durante o registro da recusa.",
        "verified_by": "VALIDATION_PIPELINE",
    }

    monkeypatch.setattr(
        order_routes,
        "uuid4",
        lambda: UUID(internal_order_id),
    )

    def fail_refusal(*args, **kwargs):
        raise RuntimeError("falha simulada na recusa por localização")

    monkeypatch.setattr(
        order_routes,
        "refuse_order_for_unconfirmed_location",
        fail_refusal,
    )

    with pytest.raises(
        RuntimeError,
        match="falha simulada na recusa por localização",
    ):
        client.post(
            "/orders",
            json=payload,
        )

    with SessionLocal() as session:
        stored_order = get_order_by_internal_id(
            session=session,
            internal_order_id=internal_order_id,
        )
        stored_refusal = get_order_refusal_by_internal_order_id(
            session=session,
            internal_order_id=internal_order_id,
        )
        history = list_order_status_history(
            session=session,
            internal_order_id=internal_order_id,
        )

    assert stored_order is None
    assert stored_refusal is None
    assert history == []


def test_rolls_back_entire_city_mismatch_refusal_when_service_fails(
    monkeypatch,
) -> None:
    from uuid import UUID

    from app.api.routes import orders as order_routes
    from app.infrastructure.database import SessionLocal
    from app.repositories.order_refusals_sqlalchemy import (
        get_order_refusal_by_internal_order_id,
    )
    from app.repositories.order_status_history_sqlalchemy import (
        list_order_status_history,
    )
    from app.repositories.orders_sqlalchemy import get_order_by_internal_id

    internal_order_id = "00000000-0000-0000-0000-000000000103"
    payload = apartment_payload("ATOMIC-CITY-ROLLBACK-001")
    payload["property"]["state"] = "RJ"
    payload["property"]["city"] = "Rio de Janeiro"
    payload["property"]["city_ibge_code"] = "3550308"

    monkeypatch.setattr(
        order_routes,
        "uuid4",
        lambda: UUID(internal_order_id),
    )

    def fail_refusal(*args, **kwargs):
        raise RuntimeError("falha simulada na recusa por inconsistência")

    monkeypatch.setattr(
        order_routes,
        "refuse_order_for_city_data_mismatch",
        fail_refusal,
    )

    with pytest.raises(
        RuntimeError,
        match="falha simulada na recusa por inconsistência",
    ):
        client.post(
            "/orders",
            json=payload,
        )

    with SessionLocal() as session:
        stored_order = get_order_by_internal_id(
            session=session,
            internal_order_id=internal_order_id,
        )
        stored_refusal = get_order_refusal_by_internal_order_id(
            session=session,
            internal_order_id=internal_order_id,
        )
        history = list_order_status_history(
            session=session,
            internal_order_id=internal_order_id,
        )

    assert stored_order is None
    assert stored_refusal is None
    assert history == []
