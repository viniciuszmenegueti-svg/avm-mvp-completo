from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


class DatasetStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class DatasetCreateRequest(BaseModel):
    data_source_id: str = Field(min_length=36, max_length=36)
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    reference_start: date | None = None
    reference_end: date | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("O nome não pode ser vazio.")
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_reference_period(self) -> "DatasetCreateRequest":
        if (
            self.reference_start is not None
            and self.reference_end is not None
            and self.reference_start > self.reference_end
        ):
            raise ValueError("A data inicial não pode ser posterior à data final.")
        return self


class DatasetUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    reference_start: date | None = None
    reference_end: date | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("O nome não pode ser vazio.")
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class DatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dataset_id: str
    data_source_id: str
    name: str
    description: str | None
    reference_start: date | None
    reference_end: date | None
    metadata: dict[str, Any]
    status: DatasetStatus
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime


class DatasetListResponse(BaseModel):
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    items: list[DatasetResponse]
