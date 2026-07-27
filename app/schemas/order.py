from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from app.schemas.property import PropertyInput


class OrderStatus(StrEnum):
    RECEIVED = "RECEIVED"
    VALIDATING_INPUT = "VALIDATING_INPUT"
    ACCEPTED = "ACCEPTED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    DELIVERING = "DELIVERING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    REFUSED = "REFUSED"
    CANCELLED = "CANCELLED"


class ConflictOfInterestDeclaration(BaseModel):
    has_conflict: bool = Field(
        default=False,
        description=(
            "Indica se foi identificado conflito de interesse relacionado "
            "à execução da avaliação."
        ),
    )
    conflict_type: str | None = Field(
        default=None,
        min_length=3,
        max_length=100,
        description="Classificação do conflito de interesse identificado.",
        examples=["RELATED_PARTY"],
    )
    description: str | None = Field(
        default=None,
        min_length=3,
        max_length=500,
        description="Descrição objetiva do conflito de interesse.",
    )
    identified_by: str | None = Field(
        default=None,
        min_length=3,
        max_length=100,
        description="Origem ou responsável pela identificação do conflito.",
        examples=["COMPLIANCE"],
    )

    @model_validator(mode="after")
    def validate_conflict_details(self) -> "ConflictOfInterestDeclaration":
        if self.has_conflict:
            if self.conflict_type is None:
                raise ValueError(
                    "conflict_type é obrigatório quando has_conflict for verdadeiro."
                )

            if self.description is None:
                raise ValueError(
                    "description é obrigatória quando has_conflict for verdadeiro."
                )

            if self.identified_by is None:
                raise ValueError(
                    "identified_by é obrigatório quando has_conflict for verdadeiro."
                )

        return self


class OrderCreate(BaseModel):
    external_order_id: str = Field(
        min_length=3,
        max_length=100,
        description="Identificador externo da Ordem de Serviço",
        examples=["CX-2026-000001"],
    )
    property: PropertyInput
    conflict_of_interest: ConflictOfInterestDeclaration = Field(
        default_factory=ConflictOfInterestDeclaration,
    )


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


class OrderStatusUpdate(BaseModel):
    status: OrderStatus = Field(
        description="Novo status da Ordem de Serviço",
        examples=["VALIDATING_INPUT"],
    )


class OrderFromPropertyAssetCreate(BaseModel):
    external_order_id: str = Field(
        min_length=3,
        max_length=100,
    )
    property_asset_id: str = Field(
        min_length=36,
        max_length=36,
    )
