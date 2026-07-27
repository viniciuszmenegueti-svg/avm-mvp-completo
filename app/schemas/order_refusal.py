from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OrderRefusalReason(StrEnum):
    MODEL_NOT_APPLICABLE = "TR_9_5_A"
    DATA_INCONSISTENCY = "TR_9_5_B"
    CONFLICT_OF_INTEREST = "TR_9_5_C"
    LOCATION_NOT_CONFIRMED = "TR_9_5_D"


class OrderRefusalCreate(BaseModel):
    reason_code: OrderRefusalReason = Field(
        description="Motivo taxativo de recusa previsto no TR §9.5",
        examples=["TR_9_5_A"],
    )
    contract_reference: str = Field(
        default="TR §9.5",
        min_length=3,
        max_length=100,
        description="Referência contratual que fundamenta a recusa",
    )
    message: str = Field(
        min_length=3,
        max_length=500,
        description="Descrição objetiva e auditável da recusa",
    )
    evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="Dossiê estruturado de evidências da recusa",
    )
    # Compatibilidade temporária com clientes da versão 0.2.0.
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Campo legado; novos clientes devem usar evidence",
    )
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Instante em que a condição de recusa foi detectada",
    )
    model_version: str | None = Field(default=None, max_length=50)
    dataset_version: str | None = Field(default=None, max_length=100)


class OrderRefusalResponse(OrderRefusalCreate):
    model_config = ConfigDict(from_attributes=True)

    refusal_id: str = Field(min_length=36, max_length=36)
    internal_order_id: str = Field(min_length=36, max_length=36)
    refused_at: datetime
