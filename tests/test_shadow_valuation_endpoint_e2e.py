from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.domain.valuation_model import ValuationModel
from app.infrastructure.database import SessionLocal
from app.main import app


client = TestClient(app)


def copacabana_apartment_payload(
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


def create_copacabana_order(
    external_order_id: str,
) -> str:
    response = client.post(
        "/orders",
        json=copacabana_apartment_payload(
            external_order_id
        ),
    )

    assert response.status_code == 201

    return response.json()["internal_order_id"]


def valuation_count() -> int:
    with SessionLocal() as session:
        statement = select(
            func.count(ValuationModel.valuation_id)
        )
        return int(
            session.scalar(statement) or 0
        )


def test_shadow_preview_executes_without_persisting() -> None:
    internal_order_id = create_copacabana_order(
        "SHADOW-E2E-COPACABANA-001"
    )

    order_before_response = client.get(
        f"/orders/{internal_order_id}"
    )

    assert order_before_response.status_code == 200

    order_before = order_before_response.json()
    status_before = order_before["status"]
    valuation_count_before = valuation_count()

    response = client.get(
        f"/orders/{internal_order_id}/"
        "shadow-valuation-preview"
    )

    assert response.status_code == 200

    result = response.json()

    assert result["internal_order_id"] == internal_order_id
    assert result["model_name"] == "RJ_FIXED_SPLIT_V3"
    assert result["model_version"] == "3"
    assert result["execution_mode"] == "SHADOW"
    assert result["contractual_validity"] is False
    assert result["formal_homologation"] is False

    assert result["estimated_value_brl"] > 0
    assert result["confidence_lower_brl"] > 0
    assert result["confidence_upper_brl"] > 0

    assert (
        result["confidence_lower_brl"]
        < result["estimated_value_brl"]
        < result["confidence_upper_brl"]
    )

    assert result["confidence_level"] == 0.8
    assert result["confidence_amplitude_percent"] > 0
    assert result["price_per_m2_brl"] > 0

    artifact_sha256 = result["artifact_sha256"]

    assert len(artifact_sha256) == 64
    assert all(
        character in "0123456789abcdef"
        for character in artifact_sha256
    )

    order_after_response = client.get(
        f"/orders/{internal_order_id}"
    )

    assert order_after_response.status_code == 200
    assert (
        order_after_response.json()["status"]
        == status_before
    )

    assert valuation_count() == valuation_count_before

    official_valuation_response = client.get(
        f"/orders/{internal_order_id}/valuation"
    )

    assert official_valuation_response.status_code == 404
    assert (
        official_valuation_response.json()["detail"]["code"]
        == "VALUATION_NOT_FOUND"
    )


def test_shadow_preview_is_deterministic_through_http() -> None:
    internal_order_id = create_copacabana_order(
        "SHADOW-E2E-COPACABANA-002"
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
    assert valuation_count() == 0


def test_shadow_preview_returns_not_found_for_unknown_order() -> None:
    internal_order_id = (
        "00000000-0000-0000-0000-000000000000"
    )

    response = client.get(
        f"/orders/{internal_order_id}/"
        "shadow-valuation-preview"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "ORDER_NOT_FOUND",
        "message": "Ordem de Serviço não encontrada.",
        "internal_order_id": internal_order_id,
    }


def test_shadow_preview_rejects_unsupported_neighborhood() -> None:
    payload = copacabana_apartment_payload(
        "SHADOW-E2E-IPANEMA-001"
    )

    property_payload = payload["property"]
    assert isinstance(property_payload, dict)

    property_payload["neighborhood"] = "Ipanema"
    property_payload["postal_code"] = "22420-000"

    create_response = client.post(
        "/orders",
        json=payload,
    )

    assert create_response.status_code == 201

    internal_order_id = (
        create_response.json()["internal_order_id"]
    )

    response = client.get(
        f"/orders/{internal_order_id}/"
        "shadow-valuation-preview"
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == (
        "SHADOW_VALUATION_NOT_APPLICABLE"
    )
    assert "Bairro fora do domínio" in (
        response.json()["detail"]["message"]
    )
    assert valuation_count() == 0
