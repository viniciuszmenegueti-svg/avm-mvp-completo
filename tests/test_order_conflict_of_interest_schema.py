import pytest
from pydantic import ValidationError

from app.schemas.order import (
    ConflictOfInterestDeclaration,
    OrderCreate,
)


def order_payload() -> dict[str, object]:
    return {
        "external_order_id": "CONFLICT-SCHEMA-001",
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


def test_uses_no_conflict_as_default() -> None:
    order = OrderCreate.model_validate(order_payload())

    assert order.conflict_of_interest.has_conflict is False
    assert order.conflict_of_interest.conflict_type is None
    assert order.conflict_of_interest.description is None
    assert order.conflict_of_interest.identified_by is None


def test_accepts_complete_conflict_declaration() -> None:
    declaration = ConflictOfInterestDeclaration(
        has_conflict=True,
        conflict_type="RELATED_PARTY",
        description="Solicitante possui vínculo com o responsável pela avaliação.",
        identified_by="COMPLIANCE",
    )

    assert declaration.has_conflict is True
    assert declaration.conflict_type == "RELATED_PARTY"
    assert declaration.identified_by == "COMPLIANCE"


@pytest.mark.parametrize(
    "missing_field",
    [
        "conflict_type",
        "description",
        "identified_by",
    ],
)
def test_rejects_incomplete_conflict_declaration(
    missing_field: str,
) -> None:
    data: dict[str, object] = {
        "has_conflict": True,
        "conflict_type": "RELATED_PARTY",
        "description": "Foi identificado vínculo entre as partes.",
        "identified_by": "COMPLIANCE",
    }

    data[missing_field] = None

    with pytest.raises(ValidationError):
        ConflictOfInterestDeclaration.model_validate(data)
