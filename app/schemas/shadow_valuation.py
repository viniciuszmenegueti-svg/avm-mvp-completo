"""Schemas da prévia de avaliação executada pelo modelo sombra."""

from pydantic import BaseModel, Field


class ShadowValuationPreviewResponse(BaseModel):
    internal_order_id: str
    model_name: str
    model_version: str
    execution_mode: str = "SHADOW"
    contractual_validity: bool = False
    formal_homologation: bool = False
    value_basis: str

    estimated_value_brl: float = Field(gt=0)
    confidence_lower_brl: float = Field(gt=0)
    confidence_upper_brl: float = Field(gt=0)
    confidence_level: float = Field(ge=0, le=1)
    confidence_amplitude_percent: float = Field(gt=0)
    price_per_m2_brl: float = Field(gt=0)

    artifact_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
    )
