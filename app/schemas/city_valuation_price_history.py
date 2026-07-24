from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.property import PropertyType


class CityValuationPriceHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int

    city_valuation_price_id: int

    city_ibge_code: str = Field(
        min_length=7,
        max_length=7,
        pattern=r"^\d{7}$",
        description="Código IBGE da cidade",
    )

    property_type: PropertyType = Field(
        description="Tipologia do imóvel",
    )

    previous_price_per_m2: Decimal = Field(
        gt=0,
        max_digits=18,
        decimal_places=2,
        description="Preço por metro quadrado anterior",
    )

    new_price_per_m2: Decimal = Field(
        gt=0,
        max_digits=18,
        decimal_places=2,
        description="Novo preço por metro quadrado",
    )

    changed_by: str = Field(
        min_length=1,
        max_length=100,
        description="Responsável pela alteração do preço",
    )

    changed_at: datetime


class CityValuationPriceHistoryListResponse(BaseModel):
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    items: list[CityValuationPriceHistoryResponse]
