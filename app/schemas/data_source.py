from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DataSourceStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class DataSourceCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    source_type: str = Field(min_length=2, max_length=50)
    responsible: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    reference_date: date | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name", "source_type", "responsible")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("O valor não pode ser vazio.")
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class DataSourceUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    source_type: str | None = Field(default=None, min_length=2, max_length=50)
    responsible: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    reference_date: date | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("name", "source_type", "responsible")
    @classmethod
    def normalize_optional_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("O valor não pode ser vazio.")
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class DataSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    data_source_id: str
    name: str
    source_type: str
    responsible: str
    description: str | None
    reference_date: date | None
    metadata: dict[str, Any]
    status: DataSourceStatus
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime


class DataSourceListResponse(BaseModel):
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    items: list[DataSourceResponse]
