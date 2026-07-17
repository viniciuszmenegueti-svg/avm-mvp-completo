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

    internal_order_id = create_response.json()[
        "internal_order_id"
    ]

    get_response = client.get(
        f"/orders/{internal_order_id}"
    )

    assert get_response.status_code == 200
    assert get_response.json()["internal_order_id"] == (
        internal_order_id
    )


def test_get_order_not_found() -> None:
    response = client.get(
        "/orders/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404


def test_get_order_with_invalid_id() -> None:
    response = client.get(
        "/orders/identificador-invalido"
    )

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

    first_internal_id = first_response.json()[
        "internal_order_id"
    ]

    detail = second_response.json()["detail"]

    assert detail["external_order_id"] == (
        "CX-2026-000001"
    )
    assert detail["internal_order_id"] == (
        first_internal_id
    )


def test_different_external_ids_are_allowed() -> None:
    first_response = client.post(
        "/orders",
        json=apartment_payload(
            "CX-2026-000001"
        ),
    )

    second_response = client.post(
        "/orders",
        json=apartment_payload(
            "CX-2026-000002"
        ),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    assert (
        first_response.json()["internal_order_id"]
        != second_response.json()["internal_order_id"]
    )


def test_rejects_order_from_unsupported_city() -> None:
    payload = apartment_payload(
        "UNSUPPORTED-CITY-001"
    )

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
            "A cidade informada não está habilitada "
            "para processamento de AVM."
        ),
        "city_ibge_code": "3205309",
    }
