from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.dataset_version import DatasetVersionStatus


class DatasetFileUploadResponse(BaseModel):
    dataset_version_id: str
    file_name: str
    storage_path: str
    checksum_sha256: str
    file_size_bytes: int = Field(ge=1)
    mime_type: str


class DatasetFileImportResultResponse(BaseModel):
    dataset_version_id: str
    status: DatasetVersionStatus
    record_count: int | None
    columns: list[str]
    delimiter: str | None
    encoding: str | None
    error_message: str | None
    processing_started_at: datetime | None
    completed_at: datetime | None
    metadata: dict[str, Any]
