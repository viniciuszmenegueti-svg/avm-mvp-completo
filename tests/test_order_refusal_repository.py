from datetime import datetime, timezone
from uuid import uuid4

from app.infrastructure.database import SessionLocal
from app.repositories.order_refusals_sqlalchemy import (
    create_order_refusal,
    get_order_refusal_by_internal_order_id,
)
from app.repositories.orders_sqlalchemy import create_order
from app.schemas.order import OrderCreate
from app.schemas.order_refusal import (
    OrderRefusalCreate,
    OrderRefusalReason,
)


def order_payload(external_order_id: str) -> dict[str, object]:
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


def create_test_order(external_order_id: str) -> str:
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


def test_creates_order_refusal() -> None:
    internal_order_id = create_test_order("REFUSAL-REPOSITORY-001")

    refusal = OrderRefusalCreate(
        reason_code=OrderRefusalReason.MODEL_NOT_APPLICABLE,
        message=("Não existe preço-base configurado para a cidade e tipologia."),
        details={
            "city_ibge_code": "3550308",
            "property_type": "APARTMENT",
        },
    )

    with SessionLocal() as session:
        database_refusal = create_order_refusal(
            session=session,
            refusal_id=str(uuid4()),
            internal_order_id=internal_order_id,
            refusal=refusal,
            refused_at=datetime.now(timezone.utc),
        )

    assert database_refusal.refusal_id
    assert database_refusal.internal_order_id == internal_order_id
    assert database_refusal.reason_code == "TR_9_5_A"
    assert database_refusal.details["city_ibge_code"] == "3550308"
    assert database_refusal.refused_at is not None


def test_gets_order_refusal_by_internal_order_id() -> None:
    internal_order_id = create_test_order("REFUSAL-REPOSITORY-002")

    refusal = OrderRefusalCreate(
        reason_code=OrderRefusalReason.LOCATION_NOT_CONFIRMED,
        message="A confiança da avaliação ficou abaixo do limite.",
    )

    with SessionLocal() as session:
        created_refusal = create_order_refusal(
            session=session,
            refusal_id=str(uuid4()),
            internal_order_id=internal_order_id,
            refusal=refusal,
            refused_at=datetime.now(timezone.utc),
        )

        stored_refusal = get_order_refusal_by_internal_order_id(
            session=session,
            internal_order_id=internal_order_id,
        )

    assert stored_refusal is not None
    assert stored_refusal.refusal_id == created_refusal.refusal_id
    assert stored_refusal.reason_code == "TR_9_5_D"
    assert stored_refusal.details == {}


def test_returns_none_for_order_without_refusal() -> None:
    internal_order_id = create_test_order("REFUSAL-REPOSITORY-003")

    with SessionLocal() as session:
        stored_refusal = get_order_refusal_by_internal_order_id(
            session=session,
            internal_order_id=internal_order_id,
        )

    assert stored_refusal is None
