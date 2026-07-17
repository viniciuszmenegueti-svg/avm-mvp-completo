from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.property import PropertyInput


class OrderStatus(StrEnum):
    RECEIVED = "RECEIVED"
    VALIDATING_INPUT = "VALIDATING_INPUT"
    COMPLETED = "COMPLETED"
    REFUSED = "REFUSED"


class OrderCreate(BaseModel):
    external_order_id: str = Field(
        min_length=3,
        max_length=100,
        description="Identificador externo da Ordem de Serviço",
        examples=["CX-2026-000001"],
    )
    property: PropertyInput


class OrderResponse(BaseModel):
    internal_order_id: str
    external_order_id: str
    status: OrderStatus
    received_at: datetime
    property: PropertyInput


class OrderListResponse(BaseModel):
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    items: list[OrderResponse]
