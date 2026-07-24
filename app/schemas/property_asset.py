from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PropertyAssetCreate(BaseModel):
    property_type: str = Field(
        min_length=2,
        max_length=50,
    )

    city_ibge_code: str = Field(
        min_length=7,
        max_length=7,
    )

    postal_code: str = Field(
        min_length=8,
        max_length=9,
    )

    neighborhood: str = Field(
        min_length=2,
        max_length=100,
    )

    street: str = Field(
        min_length=2,
        max_length=150,
    )

    number: str = Field(
        min_length=1,
        max_length=20,
    )

    private_area_m2: Decimal | None = None

    built_area_m2: Decimal | None = None

    land_area_m2: Decimal | None = None

    bedrooms: int | None = None

    bathrooms: int | None = None

    parking_spaces: int | None = None


class PropertyAssetResponse(PropertyAssetCreate):
    model_config = ConfigDict(from_attributes=True)

    property_asset_id: str = Field(
        min_length=36,
        max_length=36,
    )

    created_at: datetime
    updated_at: datetime
