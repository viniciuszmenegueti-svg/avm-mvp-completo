from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class GeocodingStatus(StrEnum):
    MATCHED = "MATCHED"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_FOUND = "NOT_FOUND"
    DATASET_NOT_LOADED = "DATASET_NOT_LOADED"
    INSUFFICIENT_POSITIONAL_QUALITY = "INSUFFICIENT_POSITIONAL_QUALITY"


class GeocodingAddressRequest(BaseModel):
    city_ibge_code: str = Field(pattern=r"^\d{7}$")
    state: str = Field(min_length=2, max_length=2)
    city: str = Field(min_length=2, max_length=100)
    postal_code: str = Field(pattern=r"^\d{5}-?\d{3}$")
    street: str = Field(min_length=2, max_length=250)
    number: str = Field(min_length=1, max_length=40)
    complement: str | None = Field(default=None, max_length=250)

    @field_validator("state")
    @classmethod
    def normalize_state(cls, value: str) -> str:
        return value.strip().upper()


class GeocodingCandidateResponse(BaseModel):
    provider: str = "CNEFE_IBGE"
    provider_record_id: str
    dataset_version: str
    source_file_sha256: str
    city_ibge_code: str
    state: str
    postal_code: str
    locality: str | None
    street: str
    number: str
    number_modifier: str | None
    complement: str | None
    latitude: float
    longitude: float
    geocoding_level: int = Field(ge=1, le=6)
    geocoding_level_description: str


class GeocodingResponse(BaseModel):
    audit_id: str
    status: GeocodingStatus
    message: str
    candidate_count: int = Field(ge=0)
    selected: GeocodingCandidateResponse | None = None
    evidence_reference: str | None = None
    automatic_coordinates_allowed: bool = False
    requires_accuracy_confirmation: bool = True
    maximum_contract_accuracy_meters: float = 50.0
