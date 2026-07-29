import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.schemas.order import LocationConfirmationDeclaration


client = TestClient(app)


def test_marks_coordinate_above_contract_accuracy_as_not_sufficient() -> None:
    declaration = LocationConfirmationDeclaration(
        is_confirmed=True,
        confirmation_method="CNEFE",
        evidence_reference="CNEFE-POINT-1",
        verified_by="GEOCODER",
        latitude=-23.550520,
        longitude=-46.633308,
        accuracy_meters=51,
    )

    assert declaration.meets_contract_accuracy is False


def test_accepts_coordinate_at_contract_accuracy_limit() -> None:
    declaration = LocationConfirmationDeclaration(
        is_confirmed=True,
        confirmation_method="CNEFE",
        evidence_reference="CNEFE-POINT-2",
        verified_by="GEOCODER",
        latitude=-23.550520,
        longitude=-46.633308,
        accuracy_meters=50,
    )

    assert declaration.meets_contract_accuracy is True


def test_rejects_accuracy_without_coordinates() -> None:
    with pytest.raises(ValidationError):
        LocationConfirmationDeclaration(
            is_confirmed=True,
            accuracy_meters=10,
        )


def test_refuses_order_when_declared_accuracy_exceeds_fifty_meters() -> None:
    response = client.post(
        "/orders",
        json={
            "external_order_id": "LOCATION-ACCURACY-051",
            "property": {
                "property_type": "APARTMENT",
                "state": "SP",
                "city": "São Paulo",
                "city_ibge_code": "3550308",
                "postal_code": "01001-000",
                "neighborhood": "Centro",
                "street": "Rua de Teste",
                "number": "100",
                "private_area_m2": 70,
                "built_area_m2": 80,
                "land_area_m2": None,
            },
            "location_confirmation": {
                "is_confirmed": True,
                "confirmation_method": "CNEFE",
                "evidence_reference": "CNEFE-POINT-3",
                "verified_by": "GEOCODER",
                "latitude": -23.550520,
                "longitude": -46.633308,
                "accuracy_meters": 51,
            },
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "REFUSED"
    refusal = client.get(
        f"/orders/{response.json()['internal_order_id']}/refusal"
    ).json()
    assert refusal["reason_code"] == "TR_9_5_D"
    assert refusal["evidence"]["accuracy_meters"] == 51
    assert refusal["evidence"]["maximum_accuracy_meters"] == 50
