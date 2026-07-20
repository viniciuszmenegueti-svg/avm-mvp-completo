from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, model_validator


class PropertyType(StrEnum):
    APARTMENT = "APARTMENT"
    HOUSE = "HOUSE"
    LAND = "LAND"


class PropertyInput(BaseModel):
    property_type: PropertyType = Field(description="Tipologia do imóvel")
    state: str = Field(
        min_length=2,
        max_length=2,
        description="Sigla da unidade federativa",
        examples=["ES"],
    )
    city: str = Field(
        min_length=2,
        max_length=100,
        description="Município do imóvel",
        examples=["Vitória"],
    )
    city_ibge_code: str = Field(
        min_length=7,
        max_length=7,
        pattern=r"^\d{7}$",
        description="Código IBGE do município",
        examples=["3205309"],
    )
    postal_code: str = Field(
        min_length=8,
        max_length=9,
        description="CEP do imóvel",
        examples=["29060-000"],
    )
    neighborhood: str = Field(
        min_length=2,
        max_length=100,
        description="Bairro do imóvel",
        examples=["Jardim da Penha"],
    )
    street: str = Field(
        min_length=2,
        max_length=150,
        description="Logradouro do imóvel",
        examples=["Avenida Fernando Ferrari"],
    )
    number: str = Field(
        min_length=1,
        max_length=20,
        description="Número do imóvel",
        examples=["100"],
    )
    complement: str | None = Field(
        default=None,
        max_length=100,
        description="Complemento, unidade ou bloco",
        examples=["Apartamento 302"],
    )
    private_area_m2: float | None = Field(
        default=None,
        gt=0,
        description="Área privativa em metros quadrados",
        examples=[72.5],
    )
    built_area_m2: float | None = Field(
        default=None,
        gt=0,
        description="Área construída em metros quadrados",
        examples=[85.0],
    )
    land_area_m2: float | None = Field(
        default=None,
        gt=0,
        description="Área do terreno em metros quadrados",
        examples=[300.0],
    )
    bedrooms: int | None = Field(
        default=None,
        ge=0,
        le=20,
        description="Quantidade de quartos",
        examples=[3],
    )
    bathrooms: int | None = Field(
        default=None,
        ge=0,
        le=20,
        description="Quantidade de banheiros",
        examples=[2],
    )
    parking_spaces: int | None = Field(
        default=None,
        ge=0,
        le=20,
        description="Quantidade de vagas",
        examples=[1],
    )

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
