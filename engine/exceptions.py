from decimal import Decimal

from app.schemas.property import PropertyType


class ValuationCalculationError(ValueError):
    """Erro base para falhas esperadas no cálculo AVM."""


class InvalidPricePerSquareMeterError(ValuationCalculationError):
    def __init__(
        self,
        price_per_m2: Decimal,
    ) -> None:
        self.price_per_m2 = price_per_m2

        super().__init__("O preço por metro quadrado deve ser maior que zero.")


class ReferenceAreaNotFoundError(ValuationCalculationError):
    def __init__(
        self,
        property_type: PropertyType,
    ) -> None:
        self.property_type = property_type

        super().__init__("Não foi possível determinar a área de referência do imóvel.")
