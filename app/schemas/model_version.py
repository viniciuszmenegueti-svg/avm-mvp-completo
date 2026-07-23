from pydantic import BaseModel, Field

from app.schemas.valuation import ValuationMethod


class ModelVersionResponse(BaseModel):
    method: ValuationMethod = Field(
        description="Método de avaliação registrado",
        examples=["RULE_BASED_V1"],
    )
    version: str = Field(
        min_length=1,
        max_length=50,
        description="Versão semântica do modelo",
        examples=["1.0.0"],
    )
    status: str = Field(
        min_length=1,
        max_length=30,
        description="Situação operacional do modelo",
        examples=["ACTIVE"],
    )
    description: str = Field(
        min_length=3,
        max_length=500,
        description="Descrição funcional do modelo",
    )
    is_default: bool = Field(
        description="Indica se este é o modelo padrão da aplicação",
    )


class ModelVersionListResponse(BaseModel):
    total: int = Field(
        ge=0,
        description="Quantidade de modelos ativos",
    )
    items: list[ModelVersionResponse]
