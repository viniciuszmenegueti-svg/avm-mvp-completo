from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.valuation import ValuationMethod
from engine.exceptions import (
    InvalidPricePerSquareMeterError,
)
from engine.registry import (
    ModelStatus,
    ModelVersionNotActiveError,
)


client = TestClient(app)


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


def house_without_base_price_payload(
    external_order_id: str,
) -> dict[str, object]:
    return {
        "external_order_id": external_order_id,
        "property": {
            "property_type": "HOUSE",
            "state": "RJ",
            "city": "Rio de Janeiro",
            "city_ibge_code": "3304557",
            "postal_code": "20010-000",
            "neighborhood": "Centro",
            "street": "Rua de Teste",
            "number": "100",
            "complement": None,
            "private_area_m2": 120,
            "built_area_m2": 140,
            "land_area_m2": 200,
            "bedrooms": 3,
            "bathrooms": 2,
            "parking_spaces": 2,
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


def create_house_without_base_price(
    external_order_id: str,
) -> str:
    response = client.post(
        "/orders",
        json=house_without_base_price_payload(external_order_id),
    )

    assert response.status_code == 201

    return response.json()["internal_order_id"]


def move_order_to_validating_input(
    internal_order_id: str,
) -> None:
    response = client.patch(
        f"/orders/{internal_order_id}/status",
        json={
            "status": "VALIDATING_INPUT",
        },
    )

    assert response.status_code == 200


def test_creates_and_reads_valuation() -> None:
    internal_order_id = create_order("VALUATION-ROUTE-001")

    move_order_to_validating_input(internal_order_id)

    create_response = client.post(f"/orders/{internal_order_id}/valuation")

    assert create_response.status_code == 201

    valuation = create_response.json()

    assert valuation["internal_order_id"] == internal_order_id
    assert valuation["method"] == "RULE_BASED_V1"
    assert valuation["estimated_value"] == "735000.00"
    assert valuation["minimum_value"] == "661500.00"
    assert valuation["maximum_value"] == "808500.00"
    assert valuation["price_per_m2"] == "10500.00"
    assert valuation["reference_area_m2"] == "70.00"
    assert valuation["confidence_score"] == "0.8000"

    get_response = client.get(f"/orders/{internal_order_id}/valuation")

    assert get_response.status_code == 200
    assert get_response.json()["valuation_id"] == valuation["valuation_id"]


def test_returns_existing_valuation_on_repeated_post() -> None:
    internal_order_id = create_order("VALUATION-ROUTE-002")

    move_order_to_validating_input(internal_order_id)

    first_response = client.post(f"/orders/{internal_order_id}/valuation")
    second_response = client.post(f"/orders/{internal_order_id}/valuation")

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert (
        second_response.json()["valuation_id"] == first_response.json()["valuation_id"]
    )


def test_returns_not_found_for_unknown_order() -> None:
    internal_order_id = "00000000-0000-0000-0000-000000000000"

    response = client.post(f"/orders/{internal_order_id}/valuation")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ORDER_NOT_FOUND"


def test_returns_conflict_when_order_is_refused() -> None:
    internal_order_id = create_house_without_base_price("VALUATION-ROUTE-REFUSED-001")

    move_order_to_validating_input(internal_order_id)

    response = client.post(f"/orders/{internal_order_id}/valuation")

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "ORDER_REFUSED",
        "message": "A Ordem de Serviço foi recusada durante a avaliação.",
        "internal_order_id": internal_order_id,
        "refusal_url": f"/orders/{internal_order_id}/refusal",
    }

    order_response = client.get(f"/orders/{internal_order_id}")

    assert order_response.status_code == 200
    assert order_response.json()["status"] == "REFUSED"


def test_returns_not_found_for_unknown_valuation() -> None:
    internal_order_id = create_order("VALUATION-ROUTE-003")

    response = client.get(f"/orders/{internal_order_id}/valuation")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "VALUATION_NOT_FOUND"


def test_rejects_valuation_before_input_validation() -> None:
    internal_order_id = create_order("VALUATION-ROUTE-004")

    response = client.post(f"/orders/{internal_order_id}/valuation")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "INVALID_STATUS_TRANSITION"


def test_returns_unprocessable_entity_for_calculation_error() -> None:
    internal_order_id = create_order("VALUATION-ROUTE-005")

    move_order_to_validating_input(internal_order_id)

    error = InvalidPricePerSquareMeterError(
        price_per_m2=Decimal("0.00"),
    )

    with patch(
        ("app.api.routes.valuations.calculate_and_store_valuation"),
        side_effect=error,
    ):
        response = client.post(f"/orders/{internal_order_id}/valuation")

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "VALUATION_CALCULATION_ERROR",
        "message": "O preço por metro quadrado deve ser maior que zero.",
        "internal_order_id": internal_order_id,
    }


def test_returns_service_unavailable_for_inactive_model() -> None:
    internal_order_id = create_order("VALUATION-ROUTE-006")

    move_order_to_validating_input(internal_order_id)

    error = ModelVersionNotActiveError(
        method=ValuationMethod.RULE_BASED_V1,
        model_status=ModelStatus.DISABLED,
    )

    with patch(
        ("app.api.routes.valuations.calculate_and_store_valuation"),
        side_effect=error,
    ):
        response = client.post(f"/orders/{internal_order_id}/valuation")

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "code": "AVM_MODEL_NOT_ACTIVE",
        "message": (
            "Modelo AVM não está ativo: RULE_BASED_V1. Status atual: DISABLED."
        ),
        "method": "RULE_BASED_V1",
        "model_status": "DISABLED",
        "internal_order_id": internal_order_id,
    }
