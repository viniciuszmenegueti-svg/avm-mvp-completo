import pytest
from pydantic import ValidationError

from app.schemas.order import (
    LocationConfirmationDeclaration,
    OrderCreate,
)


def order_payload() -> dict[str, object]:
    return {
        "external_order_id": "LOCATION-SCHEMA-001",
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


def test_uses_confirmed_location_as_default() -> None:
    order = OrderCreate.model_validate(order_payload())

    assert order.location_confirmation.is_confirmed is True
    assert order.location_confirmation.confirmation_method is None
    assert order.location_confirmation.evidence_reference is None
    assert order.location_confirmation.failure_reason is None
    assert order.location_confirmation.verified_by is None


def test_accepts_confirmed_location_with_evidence() -> None:
    declaration = LocationConfirmationDeclaration(
        is_confirmed=True,
        confirmation_method="DOCUMENT_VALIDATION",
        evidence_reference="MATRICULA-12345",
        verified_by="VALIDATION_PIPELINE",
    )

    assert declaration.is_confirmed is True
    assert declaration.confirmation_method == "DOCUMENT_VALIDATION"
    assert declaration.evidence_reference == "MATRICULA-12345"
    assert declaration.failure_reason is None
    assert declaration.verified_by == "VALIDATION_PIPELINE"


def test_accepts_unconfirmed_location_with_reason() -> None:
    declaration = LocationConfirmationDeclaration(
        is_confirmed=False,
        failure_reason=(
            "O endereço informado não pôde ser confirmado pelas evidências disponíveis."
        ),
        verified_by="VALIDATION_PIPELINE",
    )

    assert declaration.is_confirmed is False
    assert declaration.failure_reason is not None
    assert declaration.verified_by == "VALIDATION_PIPELINE"


@pytest.mark.parametrize(
    "missing_field",
    [
        "failure_reason",
        "verified_by",
    ],
)
def test_rejects_incomplete_unconfirmed_location(
    missing_field: str,
) -> None:
    data: dict[str, object] = {
        "is_confirmed": False,
        "failure_reason": (
            "O endereço informado não pôde ser confirmado pelas evidências disponíveis."
        ),
        "verified_by": "VALIDATION_PIPELINE",
    }

    data[missing_field] = None

    with pytest.raises(ValidationError):
        LocationConfirmationDeclaration.model_validate(data)


def test_rejects_failure_reason_for_confirmed_location() -> None:
    with pytest.raises(ValidationError):
        LocationConfirmationDeclaration(
            is_confirmed=True,
            failure_reason=("Falha incompatível com localização confirmada."),
        )
