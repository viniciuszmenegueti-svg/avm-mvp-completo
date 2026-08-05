from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DatasetVersionStatus(StrEnum):
    REGISTERED = "REGISTERED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DatasetVersionCreateRequest(BaseModel):
    dataset_id: str = Field(min_length=36, max_length=36)
    file_name: str = Field(min_length=1, max_length=255)
    storage_path: str = Field(min_length=1, max_length=1000)
    checksum_sha256: str = Field(min_length=64, max_length=64)
    file_size_bytes: int = Field(ge=0)
    mime_type: str | None = Field(default=None, max_length=150)
    reference_start: date | None = None
    reference_end: date | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("file_name", "storage_path")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("O valor não pode ser vazio.")
        return normalized

    @field_validator("mime_type")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("checksum_sha256")
    @classmethod
    def validate_checksum(cls, value: str) -> str:
        normalized = value.strip().lower()
        if len(normalized) != 64 or any(
            character not in "0123456789abcdef" for character in normalized
        ):
            raise ValueError("O checksum deve ser um SHA-256 hexadecimal válido.")
        return normalized

    @model_validator(mode="after")
    def validate_reference_period(self) -> "DatasetVersionCreateRequest":
        if (
            self.reference_start is not None
            and self.reference_end is not None
            and self.reference_start > self.reference_end
        ):
            raise ValueError("A data inicial não pode ser posterior à data final.")
        return self


class DatasetVersionCompleteRequest(BaseModel):
    record_count: int = Field(ge=0)
    metadata: dict[str, Any] | None = None


class DatasetVersionFailRequest(BaseModel):
    error_message: str = Field(min_length=1, max_length=5000)

    @field_validator("error_message")
    @classmethod
    def strip_error(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("A mensagem de erro não pode ser vazia.")
        return normalized


class DatasetVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dataset_version_id: str
    dataset_id: str
    version_number: int
    file_name: str
    storage_path: str
    checksum_sha256: str
    file_size_bytes: int
    mime_type: str | None
    reference_start: date | None
    reference_end: date | None
    record_count: int | None
    status: DatasetVersionStatus
    error_message: str | None
    metadata: dict[str, Any]
    processing_started_at: datetime | None
    completed_at: datetime | None
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime


class DatasetVersionListResponse(BaseModel):
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    items: list[DatasetVersionResponse]
