from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class OrderRefusalReason(StrEnum):
    MISSING_BASE_PRICE = "MISSING_BASE_PRICE"
    INSUFFICIENT_MARKET_DATA = "INSUFFICIENT_MARKET_DATA"
    UNSUPPORTED_PROPERTY_TYPE = "UNSUPPORTED_PROPERTY_TYPE"
    PROPERTY_DATA_INCONSISTENT = "PROPERTY_DATA_INCONSISTENT"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"


class OrderRefusalCreate(BaseModel):
    reason_code: OrderRefusalReason = Field(
        description="Código estruturado do motivo da recusa",
        examples=["MISSING_BASE_PRICE"],
    )
    message: str = Field(
        min_length=3,
        max_length=500,
        description="Descrição legível do motivo da recusa",
        examples=["Não existe preço-base configurado para a cidade e tipologia."],
    )
    details: dict[str, str] = Field(
        default_factory=dict,
        description="Informações adicionais relacionadas à recusa",
        examples=[
            {
                "city_ibge_code": "3550308",
                "property_type": "APARTMENT",
            }
        ],
    )


class OrderRefusalResponse(OrderRefusalCreate):
    model_config = ConfigDict(from_attributes=True)

    refusal_id: str = Field(
        min_length=36,
        max_length=36,
        description="Identificador interno da recusa",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    internal_order_id: str = Field(
        min_length=36,
        max_length=36,
        description="Identificador interno da Ordem de Serviço",
        examples=["550e8400-e29b-41d4-a716-446655440001"],
    )
    refused_at: datetime = Field(
        description="Data e hora em que a ordem foi recusada",
    )
