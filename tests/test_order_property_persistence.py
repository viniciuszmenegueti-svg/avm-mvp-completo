from datetime import datetime, timezone
from uuid import uuid4

from app.domain.order_model import OrderModel
from app.domain.property_model import PropertyModel
from app.infrastructure.database import SessionLocal
from app.repositories.orders_sqlalchemy import (
    create_order,
    get_order_by_internal_id,
)
from app.schemas.order import OrderCreate


def apartment_payload(
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


def test_creates_normalized_property_record() -> None:
    internal_order_id = str(uuid4())

    order = OrderCreate.model_validate(apartment_payload("PROPERTY-PERSISTENCE-001"))

    with SessionLocal() as session:
        create_order(
            session=session,
            order=order,
            internal_order_id=internal_order_id,
            received_at=datetime.now(timezone.utc),
        )

        database_order = session.get(
            OrderModel,
            internal_order_id,
        )
        database_property = session.get(
            PropertyModel,
            internal_order_id,
        )

    assert database_order is not None
    assert database_order.property_json

    assert database_property is not None
    assert database_property.internal_order_id == internal_order_id
    assert database_property.property_type == "APARTMENT"
    assert database_property.city_ibge_code == "3550308"
    assert database_property.private_area_m2 is not None
    assert float(database_property.private_area_m2) == 70
    assert database_property.land_area_m2 is None


def test_reads_property_from_normalized_record() -> None:
    internal_order_id = str(uuid4())

    order = OrderCreate.model_validate(apartment_payload("PROPERTY-PERSISTENCE-002"))

    with SessionLocal() as session:
        create_order(
            session=session,
            order=order,
            internal_order_id=internal_order_id,
            received_at=datetime.now(timezone.utc),
        )

        database_order = session.get(
            OrderModel,
            internal_order_id,
        )

        assert database_order is not None

        database_order.property_json = "{}"
        session.commit()

        stored_order = get_order_by_internal_id(
            session=session,
            internal_order_id=internal_order_id,
        )

    assert stored_order is not None
    assert stored_order.property.property_type.value == "APARTMENT"
    assert stored_order.property.city == "São Paulo"
    assert stored_order.property.city_ibge_code == "3550308"
    assert stored_order.property.private_area_m2 == 70
