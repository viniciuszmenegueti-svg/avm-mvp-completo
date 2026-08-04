from datetime import datetime
from enum import StrEnum
from typing import ClassVar, Self

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


class OrderSlaOutcome(StrEnum):
    PENDING = "PENDING"
    WITHIN_SLA = "WITHIN_SLA"
    BREACHED = "BREACHED"


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
    def validate_conflict_details(self) -> Self:
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


class LocationConfirmationDeclaration(BaseModel):
    MAXIMUM_CONTRACT_ACCURACY_METERS: ClassVar[float] = 50.0

    is_confirmed: bool = Field(
        default=True,
        description=(
            "Indica se a localização do imóvel foi confirmada por evidência "
            "suficiente para execução da avaliação."
        ),
    )
    confirmation_method: str | None = Field(
        default=None,
        min_length=3,
        max_length=100,
        description="Método utilizado para confirmar a localização.",
        examples=["DOCUMENT_VALIDATION"],
    )
    evidence_reference: str | None = Field(
        default=None,
        min_length=3,
        max_length=250,
        description="Referência da evidência utilizada na confirmação.",
        examples=["MATRICULA-12345"],
    )
    failure_reason: str | None = Field(
        default=None,
        min_length=3,
        max_length=500,
        description=("Motivo pelo qual a localização não pôde ser confirmada."),
    )
    verified_by: str | None = Field(
        default=None,
        min_length=3,
        max_length=100,
        description="Origem ou responsável pela verificação da localização.",
        examples=["VALIDATION_PIPELINE"],
    )
    geocoding_audit_id: str | None = Field(
        default=None,
        min_length=36,
        max_length=36,
        description=(
            "Identificador da auditoria MATCHED que originou as coordenadas "
            "quando confirmation_method for CNEFE_IBGE."
        ),
    )
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    accuracy_meters: float | None = Field(
        default=None,
        ge=0,
        description="Imprecisão declarada da coordenada em metros.",
    )

    @model_validator(mode="after")
    def validate_location_confirmation(self) -> Self:
        uses_cnefe = (self.confirmation_method or "").strip().upper() == "CNEFE_IBGE"
        if uses_cnefe and self.geocoding_audit_id is None:
            raise ValueError(
                "geocoding_audit_id é obrigatório para o método CNEFE_IBGE."
            )
        if not uses_cnefe and self.geocoding_audit_id is not None:
            raise ValueError(
                "geocoding_audit_id somente pode ser usado com CNEFE_IBGE."
            )

        has_latitude = self.latitude is not None
        has_longitude = self.longitude is not None
        if has_latitude != has_longitude:
            raise ValueError("latitude e longitude devem ser informadas em conjunto.")
        if self.accuracy_meters is not None and not (has_latitude and has_longitude):
            raise ValueError("accuracy_meters exige latitude e longitude declaradas.")

        if self.is_confirmed:
            if self.failure_reason is not None:
                raise ValueError(
                    "failure_reason não deve ser informado quando "
                    "is_confirmed for verdadeiro."
                )

            return self

        if self.failure_reason is None:
            raise ValueError(
                "failure_reason é obrigatório quando is_confirmed for falso."
            )

        if self.verified_by is None:
            raise ValueError("verified_by é obrigatório quando is_confirmed for falso.")

        return self

    @property
    def meets_contract_accuracy(self) -> bool:
        return self.is_confirmed and (
            self.accuracy_meters is None
            or self.accuracy_meters <= self.MAXIMUM_CONTRACT_ACCURACY_METERS
        )

    @property
    def has_auditable_contract_coordinates(self) -> bool:
        return (
            self.is_confirmed
            and self.latitude is not None
            and self.longitude is not None
            and self.accuracy_meters is not None
            and self.accuracy_meters <= self.MAXIMUM_CONTRACT_ACCURACY_METERS
            and self.confirmation_method is not None
            and self.evidence_reference is not None
            and self.verified_by is not None
        )


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
    location_confirmation: LocationConfirmationDeclaration = Field(
        default_factory=LocationConfirmationDeclaration,
    )


class OrderResponse(BaseModel):
    internal_order_id: str
    external_order_id: str
    status: OrderStatus
    received_at: datetime
    response_deadline_at: datetime
    responded_at: datetime | None = None
    response_elapsed_seconds: float = Field(ge=0)
    sla_outcome: OrderSlaOutcome
    property: PropertyInput
    location_confirmation: LocationConfirmationDeclaration = Field(
        default_factory=LocationConfirmationDeclaration,
    )


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
    conflict_of_interest: ConflictOfInterestDeclaration = Field(
        default_factory=ConflictOfInterestDeclaration,
    )
    location_confirmation: LocationConfirmationDeclaration = Field(
        default_factory=LocationConfirmationDeclaration,
    )
