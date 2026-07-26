from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class ValuationMethod(StrEnum):
    RULE_BASED_V1 = "RULE_BASED_V1"


class ValuationResponse(BaseModel):
    valuation_id: str
    internal_order_id: str
    method: ValuationMethod
    model_version: str = Field(min_length=1, max_length=50)
    estimated_value: Decimal = Field(gt=0, decimal_places=2)
    minimum_value: Decimal = Field(gt=0, decimal_places=2)
    maximum_value: Decimal = Field(gt=0, decimal_places=2)
    price_per_m2: Decimal = Field(gt=0, decimal_places=2)
    reference_area_m2: Decimal = Field(gt=0, decimal_places=2)
    confidence_score: Decimal = Field(ge=0, le=1, decimal_places=4)
    factors: dict[str, str] = Field(default_factory=dict)
    confidence_reasons: list[str] = Field(default_factory=list)
    calculated_at: datetime
