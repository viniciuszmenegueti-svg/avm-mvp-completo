from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from app.schemas.property import (
    PropertyInput,
    PropertyType,
)
from app.schemas.valuation import ValuationMethod
from engine.exceptions import (
    InvalidPricePerSquareMeterError,
    ReferenceAreaNotFoundError,
)


MONEY_QUANTIZER = Decimal("0.01")
SCORE_QUANTIZER = Decimal("0.0001")

MINIMUM_FACTOR = Decimal("0.90")
MAXIMUM_FACTOR = Decimal("1.10")


@dataclass(frozen=True)
class ValuationCalculation:
    method: ValuationMethod
    estimated_value: Decimal
    minimum_value: Decimal
    maximum_value: Decimal
    price_per_m2: Decimal
    reference_area_m2: Decimal
    confidence_score: Decimal
    factors: dict[str, str] = field(default_factory=dict)
    confidence_reasons: list[str] = field(default_factory=list)


def quantize_money(
    value: Decimal,
) -> Decimal:
    return value.quantize(
        MONEY_QUANTIZER,
        rounding=ROUND_HALF_UP,
    )


def get_reference_area(
    property_data: PropertyInput,
) -> Decimal:
    if property_data.property_type == PropertyType.APARTMENT:
        area = property_data.private_area_m2
    elif property_data.property_type == PropertyType.HOUSE:
        area = property_data.built_area_m2
    else:
        area = property_data.land_area_m2

    if area is None:
        raise ReferenceAreaNotFoundError(
            property_type=property_data.property_type,
        )

    return Decimal(str(area)).quantize(
        MONEY_QUANTIZER,
        rounding=ROUND_HALF_UP,
    )


def calculate_confidence_details(
    property_data: PropertyInput,
) -> tuple[Decimal, list[str]]:
    score = Decimal("0.6000")

    optional_fields = (
        property_data.bedrooms,
        property_data.bathrooms,
        property_data.parking_spaces,
        property_data.complement,
    )

    completed_fields = sum(field is not None for field in optional_fields)

    score += Decimal(completed_fields) * Decimal("0.0500")
    reasons = [
        "Preço-base disponível para cidade e tipologia.",
        "Área de referência válida.",
    ]
    if completed_fields:
        reasons.append(f"{completed_fields} atributos complementares informados.")
    else:
        reasons.append("Atributos complementares não informados reduzem a confiança.")
    normalized = min(score, Decimal("0.8000")).quantize(
        SCORE_QUANTIZER, rounding=ROUND_HALF_UP
    )
    return normalized, reasons


def calculate_confidence_score(property_data: PropertyInput) -> Decimal:
    return calculate_confidence_details(property_data)[0]


def calculate_valuation(
    property_data: PropertyInput,
    price_per_m2: Decimal,
) -> ValuationCalculation:
    if price_per_m2 <= 0:
        raise InvalidPricePerSquareMeterError(
            price_per_m2=price_per_m2,
        )

    reference_area_m2 = get_reference_area(property_data)

    normalized_price_per_m2 = quantize_money(price_per_m2)

    estimated_value = quantize_money(reference_area_m2 * normalized_price_per_m2)

    minimum_value = quantize_money(estimated_value * MINIMUM_FACTOR)

    maximum_value = quantize_money(estimated_value * MAXIMUM_FACTOR)

    confidence_score, confidence_reasons = calculate_confidence_details(property_data)

    return ValuationCalculation(
        method=ValuationMethod.RULE_BASED_V1,
        estimated_value=estimated_value,
        minimum_value=minimum_value,
        maximum_value=maximum_value,
        price_per_m2=normalized_price_per_m2,
        reference_area_m2=reference_area_m2,
        confidence_score=confidence_score,
        factors={
            "base_price_per_m2": str(normalized_price_per_m2),
            "reference_area_m2": str(reference_area_m2),
            "area_factor": "1.0000",
            "location_factor": "1.0000",
            "characteristics_factor": "1.0000",
        },
        confidence_reasons=confidence_reasons,
    )
