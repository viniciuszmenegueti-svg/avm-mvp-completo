from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class ValuationMethod(StrEnum):
    RULE_BASED_V1 = "RULE_BASED_V1"
    LINEAR_REGRESSION_OLS = "LINEAR_REGRESSION_OLS"


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
    execution_mode: str = Field(default="DEMONSTRATION", max_length=40)
    statistical_model_id: str | None = Field(default=None, max_length=36)
    model_artifact_sha256: str | None = Field(default=None, max_length=64)
    dataset_sha256: str | None = Field(default=None, max_length=64)
    contractual_validity: bool = False
    calculated_at: datetime
