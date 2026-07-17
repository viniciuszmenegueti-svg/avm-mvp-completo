from pydantic import BaseModel, ConfigDict, Field


class CityResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    city_ibge_code: str = Field(
        min_length=7,
        max_length=7,
        description="Código IBGE do município",
        examples=["3550308"],
    )

    name: str = Field(
        description="Nome oficial do município",
        examples=["São Paulo"],
    )

    state: str = Field(
        min_length=2,
        max_length=2,
        description="Sigla da unidade federativa",
        examples=["SP"],
    )

    active: bool
