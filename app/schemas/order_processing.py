from enum import StrEnum

from pydantic import BaseModel

from app.schemas.order import OrderResponse
from app.schemas.order_refusal import OrderRefusalResponse
from app.schemas.valuation import ValuationResponse


class OrderProcessOutcome(StrEnum):
    COMPLETED = "COMPLETED"
    REFUSED = "REFUSED"
    CANCELLED = "CANCELLED"


class OrderProcessResponse(BaseModel):
    outcome: OrderProcessOutcome
    order: OrderResponse
    valuation: ValuationResponse | None = None
    refusal: OrderRefusalResponse | None = None
    contractual_delivery_enabled: bool = False
