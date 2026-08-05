"""Schemas administrativos das execuções do modelo sombra."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ShadowExecutionResultStatus(StrEnum):
    SUCCESS = "SUCCESS"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ShadowValuationExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    execution_id: str
    internal_order_id: str
    request_id: str | None
    requested_by: str

    result_status: ShadowExecutionResultStatus

    model_name: str | None
    model_version: str | None

    execution_mode: str
    contractual_validity: bool
    formal_homologation: bool

    value_basis: str | None

    estimated_value_brl: Decimal | None
    confidence_lower_brl: Decimal | None
    confidence_upper_brl: Decimal | None
    confidence_level: Decimal | None
    confidence_amplitude_percent: Decimal | None
    price_per_m2_brl: Decimal | None

    artifact_sha256: str | None

    neighborhood: str | None
    private_area_m2: Decimal | None
    bedrooms: int | None
    bathrooms: int | None
    parking_spaces: int | None

    error_message: str | None
    executed_at: datetime


class ShadowValuationExecutionListResponse(BaseModel):
    internal_order_id: str
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    items: list[ShadowValuationExecutionResponse]


class ShadowValuationExecutionSearchResponse(BaseModel):
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    items: list[ShadowValuationExecutionResponse]

