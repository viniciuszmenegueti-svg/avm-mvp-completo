from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DatasetImportExecutionStatus(StrEnum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DatasetImportRowStatus(StrEnum):
    VALID = "VALID"
    INVALID = "INVALID"
    DUPLICATE = "DUPLICATE"


class DatasetImportFieldType(StrEnum):
    STRING = "STRING"
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    DATE = "DATE"
    BOOLEAN = "BOOLEAN"


class DatasetImportStagingRequest(BaseModel):
    required_fields: list[str] = Field(default_factory=list)
    field_types: dict[str, DatasetImportFieldType] = Field(default_factory=dict)
    date_format: str = Field(default="%Y-%m-%d", min_length=1, max_length=50)
    batch_size: int = Field(default=500, ge=1, le=5000)
    force_reprocess: bool = False

    @field_validator("required_fields")
    @classmethod
    def normalize_required_fields(cls, values: list[str]) -> list[str]:
        normalized = []
        seen = set()
        for value in values:
            item = value.strip()
            if not item:
                raise ValueError("Os campos obrigatórios não podem ser vazios.")
            key = item.casefold()
            if key not in seen:
                normalized.append(item)
                seen.add(key)
        return normalized

    @field_validator("field_types")
    @classmethod
    def normalize_field_names(
        cls, values: dict[str, DatasetImportFieldType]
    ) -> dict[str, DatasetImportFieldType]:
        result: dict[str, DatasetImportFieldType] = {}
        for key, value in values.items():
            normalized = key.strip()
            if not normalized:
                raise ValueError("O nome do campo tipado não pode ser vazio.")
            result[normalized] = value
        return result


class DatasetImportStagingSummaryResponse(BaseModel):
    execution_id: str
    dataset_version_id: str
    status: DatasetImportExecutionStatus
    total_rows: int = Field(ge=0)
    valid_rows: int = Field(ge=0)
    invalid_rows: int = Field(ge=0)
    duplicate_rows: int = Field(ge=0)
    validation_schema: dict[str, Any]
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None
    created_by: str
    created_at: datetime


class DatasetImportRejectedRowResponse(BaseModel):
    row_id: str
    execution_id: str
    dataset_version_id: str
    line_number: int = Field(ge=2)
    status: DatasetImportRowStatus
    original: dict[str, Any]
    normalized: dict[str, Any] | None
    errors: list[str]
    row_hash: str | None
    created_at: datetime


class DatasetImportRejectedRowsListResponse(BaseModel):
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    items: list[DatasetImportRejectedRowResponse]
