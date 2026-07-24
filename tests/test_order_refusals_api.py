from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.infrastructure.database import SessionLocal
from app.main import app
from app.repositories.order_refusals_sqlalchemy import (
    create_order_refusal,
)
from app.repositories.orders_sqlalchemy import create_order
from app.schemas.order import OrderCreate
from app.schemas.order_refusal import (
    OrderRefusalCreate,
    OrderRefusalReason,
)


client = TestClient(app)


def order_payload(
    external_order_id: str,
) -> dict[str, object]:
    return {
        "external_order_id": external_order_id,
        "property": {
            "property_type": "APARTMENT",
            "state": "SP",
            "city": "São Paulo",
            "city_ibge_code": "3550308",
            "postal_code": "01001-000",
            "neighborhood": "Centro",
            "street": "Rua de Teste",
            "number": "100",
            "complement": "Apartamento 10",
            "private_area_m2": 70,
            "built_area_m2": 80,
            "land_area_m2": None,
            "bedrooms": 2,
            "bathrooms": 2,
            "parking_spaces": 1,
        },
    }


def create_test_order(
    external_order_id: str,
) -> str:
    internal_order_id = str(uuid4())

    order = OrderCreate.model_validate(order_payload(external_order_id))

    with SessionLocal() as session:
        create_order(
            session=session,
            order=order,
            internal_order_id=internal_order_id,
            received_at=datetime.now(timezone.utc),
        )

    return internal_order_id


def test_gets_order_refusal() -> None:
    internal_order_id = create_test_order("REFUSAL-API-001")

    refusal = OrderRefusalCreate(
        reason_code=OrderRefusalReason.MISSING_BASE_PRICE,
        message=("Não existe preço-base configurado para a cidade e tipologia."),
        details={
            "city_ibge_code": "3550308",
            "property_type": "APARTMENT",
        },
    )

    with SessionLocal() as session:
        created_refusal = create_order_refusal(
            session=session,
            refusal_id=str(uuid4()),
            internal_order_id=internal_order_id,
            refusal=refusal,
            refused_at=datetime.now(timezone.utc),
        )

    response = client.get(f"/orders/{internal_order_id}/refusal")

    assert response.status_code == 200

    body = response.json()

    assert body["refusal_id"] == created_refusal.refusal_id
    assert body["internal_order_id"] == internal_order_id
    assert body["reason_code"] == "MISSING_BASE_PRICE"
    assert body["message"] == (
        "Não existe preço-base configurado para a cidade e tipologia."
    )
    assert body["details"] == {
        "city_ibge_code": "3550308",
        "property_type": "APARTMENT",
    }
    assert body["refused_at"]


def test_get_refusal_returns_order_not_found() -> None:
    internal_order_id = "00000000-0000-0000-0000-000000000000"

    response = client.get(f"/orders/{internal_order_id}/refusal")

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "ORDER_NOT_FOUND",
        "message": "Ordem de Serviço não encontrada.",
        "internal_order_id": internal_order_id,
    }


def test_get_refusal_returns_refusal_not_found() -> None:
    internal_order_id = create_test_order("REFUSAL-API-002")

    response = client.get(f"/orders/{internal_order_id}/refusal")

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "ORDER_REFUSAL_NOT_FOUND",
        "message": "A ordem não possui recusa registrada.",
        "internal_order_id": internal_order_id,
    }


def test_get_refusal_rejects_invalid_order_id() -> None:
    response = client.get("/orders/identificador-invalido/refusal")

    assert response.status_code == 422
