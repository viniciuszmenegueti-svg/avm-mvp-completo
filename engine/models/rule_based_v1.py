from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.schemas.property import PropertyInput, PropertyType
from app.schemas.valuation import ValuationMethod


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


def quantize_money(value: Decimal) -> Decimal:
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
        raise ValueError("Não foi possível determinar a área de referência.")

    return Decimal(str(area)).quantize(
        MONEY_QUANTIZER,
        rounding=ROUND_HALF_UP,
    )


def calculate_confidence_score(
    property_data: PropertyInput,
) -> Decimal:
    score = Decimal("0.6000")

    optional_fields = (
        property_data.bedrooms,
        property_data.bathrooms,
        property_data.parking_spaces,
        property_data.complement,
    )

    completed_fields = sum(field is not None for field in optional_fields)

    score += Decimal(completed_fields) * Decimal("0.0500")

    return min(
        score,
        Decimal("0.8000"),
    ).quantize(
        SCORE_QUANTIZER,
        rounding=ROUND_HALF_UP,
    )


def calculate_valuation(
    property_data: PropertyInput,
    price_per_m2: Decimal,
) -> ValuationCalculation:
    if price_per_m2 <= 0:
        raise ValueError("O preço por metro quadrado deve ser maior que zero.")

    reference_area_m2 = get_reference_area(property_data)

    normalized_price_per_m2 = quantize_money(price_per_m2)

    estimated_value = quantize_money(reference_area_m2 * normalized_price_per_m2)

    minimum_value = quantize_money(estimated_value * MINIMUM_FACTOR)

    maximum_value = quantize_money(estimated_value * MAXIMUM_FACTOR)

    confidence_score = calculate_confidence_score(property_data)

    return ValuationCalculation(
        method=ValuationMethod.RULE_BASED_V1,
        estimated_value=estimated_value,
        minimum_value=minimum_value,
        maximum_value=maximum_value,
        price_per_m2=normalized_price_per_m2,
        reference_area_m2=reference_area_m2,
        confidence_score=confidence_score,
    )
