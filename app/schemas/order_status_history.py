from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.order import OrderStatus


class OrderStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ge=1,
        description="Identificador do registro de histórico",
    )
    internal_order_id: str = Field(
        min_length=36,
        max_length=36,
        description="Identificador interno da Ordem de Serviço",
    )
    previous_status: OrderStatus
    new_status: OrderStatus
    changed_at: datetime
    changed_by: str = Field(min_length=1, max_length=100)
    request_id: str = Field(min_length=1, max_length=128)
    reason_code: str = Field(min_length=1, max_length=100)
    context: dict[str, Any] = Field(default_factory=dict)
