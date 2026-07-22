from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class ValuationMethod(StrEnum):
    RULE_BASED_V1 = "RULE_BASED_V1"


class ValuationResponse(BaseModel):
    valuation_id: str = Field(
        description="Identificador interno da avaliação",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    internal_order_id: str = Field(
        description="Identificador interno da Ordem de Serviço",
        examples=["550e8400-e29b-41d4-a716-446655440001"],
    )
    method: ValuationMethod = Field(
        description="Método utilizado para calcular a avaliação",
        examples=["RULE_BASED_V1"],
    )
    estimated_value: Decimal = Field(
        gt=0,
        decimal_places=2,
        description="Valor estimado do imóvel em reais",
        examples=["525000.00"],
    )
    minimum_value: Decimal = Field(
        gt=0,
        decimal_places=2,
        description="Limite inferior estimado em reais",
        examples=["472500.00"],
    )
    maximum_value: Decimal = Field(
        gt=0,
        decimal_places=2,
        description="Limite superior estimado em reais",
        examples=["577500.00"],
    )
    price_per_m2: Decimal = Field(
        gt=0,
        decimal_places=2,
        description="Valor estimado por metro quadrado",
        examples=["7500.00"],
    )
    reference_area_m2: Decimal = Field(
        gt=0,
        decimal_places=2,
        description="Área utilizada como referência no cálculo",
        examples=["70.00"],
    )
    confidence_score: Decimal = Field(
        ge=0,
        le=1,
        decimal_places=4,
        description="Índice de confiança da avaliação entre zero e um",
        examples=["0.7500"],
    )
    calculated_at: datetime = Field(
        description="Data e hora em que a avaliação foi calculada",
    )
