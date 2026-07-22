from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.schemas.property import PropertyInput, PropertyType
from app.schemas.valuation import ValuationMethod


MONEY_QUANTIZER = Decimal("0.01")
SCORE_QUANTIZER = Decimal("0.0001")

MINIMUM_FACTOR = Decimal("0.90")
MAXIMUM_FACTOR = Decimal("1.10")


BASE_PRICE_PER_M2: dict[
    str,
    dict[PropertyType, Decimal],
] = {
    "3304557": {
        PropertyType.APARTMENT: Decimal("9500.00"),
        PropertyType.HOUSE: Decimal("7200.00"),
        PropertyType.LAND: Decimal("4800.00"),
    },
    "3550308": {
        PropertyType.APARTMENT: Decimal("10500.00"),
        PropertyType.HOUSE: Decimal("7800.00"),
        PropertyType.LAND: Decimal("5200.00"),
    },
    "5300108": {
        PropertyType.APARTMENT: Decimal("8200.00"),
        PropertyType.HOUSE: Decimal("6500.00"),
        PropertyType.LAND: Decimal("4000.00"),
    },
    "2927408": {
        PropertyType.APARTMENT: Decimal("6800.00"),
        PropertyType.HOUSE: Decimal("5200.00"),
        PropertyType.LAND: Decimal("3200.00"),
    },
    "3106200": {
        PropertyType.APARTMENT: Decimal("7600.00"),
        PropertyType.HOUSE: Decimal("5900.00"),
        PropertyType.LAND: Decimal("3600.00"),
    },
    "4106902": {
        PropertyType.APARTMENT: Decimal("7900.00"),
        PropertyType.HOUSE: Decimal("6100.00"),
        PropertyType.LAND: Decimal("3800.00"),
    },
    "2611606": {
        PropertyType.APARTMENT: Decimal("6500.00"),
        PropertyType.HOUSE: Decimal("5000.00"),
        PropertyType.LAND: Decimal("3100.00"),
    },
    "2304400": {
        PropertyType.APARTMENT: Decimal("6400.00"),
        PropertyType.HOUSE: Decimal("4900.00"),
        PropertyType.LAND: Decimal("3000.00"),
    },
    "5208707": {
        PropertyType.APARTMENT: Decimal("6100.00"),
        PropertyType.HOUSE: Decimal("4700.00"),
        PropertyType.LAND: Decimal("2900.00"),
    },
    "4314902": {
        PropertyType.APARTMENT: Decimal("7000.00"),
        PropertyType.HOUSE: Decimal("5400.00"),
        PropertyType.LAND: Decimal("3300.00"),
    },
}


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


def get_base_price_per_m2(
    property_data: PropertyInput,
) -> Decimal:
    city_prices = BASE_PRICE_PER_M2.get(property_data.city_ibge_code)

    if city_prices is None:
        raise ValueError("Não existe preço-base configurado para a cidade.")

    return city_prices[property_data.property_type]


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
) -> ValuationCalculation:
    reference_area_m2 = get_reference_area(property_data)

    price_per_m2 = get_base_price_per_m2(property_data)

    estimated_value = quantize_money(reference_area_m2 * price_per_m2)

    minimum_value = quantize_money(estimated_value * MINIMUM_FACTOR)

    maximum_value = quantize_money(estimated_value * MAXIMUM_FACTOR)

    confidence_score = calculate_confidence_score(property_data)

    return ValuationCalculation(
        method=ValuationMethod.RULE_BASED_V1,
        estimated_value=estimated_value,
        minimum_value=minimum_value,
        maximum_value=maximum_value,
        price_per_m2=price_per_m2,
        reference_area_m2=reference_area_m2,
        confidence_score=confidence_score,
    )
