from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.property import PropertyType


class PropertyAssetCreate(BaseModel):
    property_type: PropertyType = Field(description="Tipologia do imóvel")
    city_ibge_code: str = Field(min_length=7, max_length=7, pattern=r"^\d{7}$")
    postal_code: str = Field(min_length=8, max_length=9)
    neighborhood: str = Field(min_length=2, max_length=100)
    street: str = Field(min_length=2, max_length=150)
    number: str = Field(min_length=1, max_length=20)
    complement: str | None = Field(default=None, max_length=100)
    private_area_m2: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=2
    )
    built_area_m2: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=2
    )
    land_area_m2: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=2
    )
    bedrooms: int | None = Field(default=None, ge=0, le=20)
    bathrooms: int | None = Field(default=None, ge=0, le=20)
    parking_spaces: int | None = Field(default=None, ge=0, le=20)

    @model_validator(mode="after")
    def validate_property_areas(self) -> Self:
        if self.property_type == PropertyType.APARTMENT:
            if self.private_area_m2 is None:
                raise ValueError("Apartamento deve possuir private_area_m2.")
            if self.land_area_m2 is not None:
                raise ValueError("Apartamento não deve possuir land_area_m2.")
        if self.property_type == PropertyType.HOUSE:
            if self.built_area_m2 is None:
                raise ValueError("Casa deve possuir built_area_m2.")
            if self.land_area_m2 is None:
                raise ValueError("Casa deve possuir land_area_m2.")
        if self.property_type == PropertyType.LAND:
            if self.land_area_m2 is None:
                raise ValueError("Terreno deve possuir land_area_m2.")
            if self.private_area_m2 is not None:
                raise ValueError("Terreno não deve possuir private_area_m2.")
            if self.built_area_m2 is not None:
                raise ValueError("Terreno não deve possuir built_area_m2.")
        return self


class PropertyAssetUpdate(BaseModel):
    postal_code: str | None = Field(default=None, min_length=8, max_length=9)
    neighborhood: str | None = Field(default=None, min_length=2, max_length=100)
    street: str | None = Field(default=None, min_length=2, max_length=150)
    number: str | None = Field(default=None, min_length=1, max_length=20)
    complement: str | None = Field(default=None, max_length=100)
    private_area_m2: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=2
    )
    built_area_m2: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=2
    )
    land_area_m2: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=2
    )
    bedrooms: int | None = Field(default=None, ge=0, le=20)
    bathrooms: int | None = Field(default=None, ge=0, le=20)
    parking_spaces: int | None = Field(default=None, ge=0, le=20)


class PropertyAssetResponse(PropertyAssetCreate):
    model_config = ConfigDict(from_attributes=True)
    property_asset_id: str = Field(min_length=36, max_length=36)
    created_at: datetime
    updated_at: datetime


class PropertyAssetListResponse(BaseModel):
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    items: list[PropertyAssetResponse]
