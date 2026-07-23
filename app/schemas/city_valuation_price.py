from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.property import PropertyType


class CityValuationPriceUpdate(BaseModel):
    price_per_m2: Decimal = Field(
        gt=0,
        max_digits=18,
        decimal_places=2,
        description="Novo preço-base por metro quadrado",
        examples=[10500.00],
    )


class CityValuationPriceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    city_ibge_code: str = Field(
        min_length=7,
        max_length=7,
        pattern=r"^\d{7}$",
        description="Código IBGE da cidade",
    )
    property_type: PropertyType = Field(
        description="Tipologia do imóvel",
    )
    price_per_m2: Decimal = Field(
        gt=0,
        max_digits=18,
        decimal_places=2,
        description="Preço-base por metro quadrado",
    )
    created_at: datetime
    updated_at: datetime
