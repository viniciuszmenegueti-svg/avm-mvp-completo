from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.core.admin_auth import require_admin_api_key
from app.infrastructure.dependencies import DatabaseSession
from app.schemas.dataset_file_import import (
    DatasetFileImportResultResponse,
    DatasetFileUploadResponse,
)
from app.services.dataset_file_import_service import (
    DatasetFileAlreadyUploadedError,
    DatasetFileChecksumMismatchError,
    DatasetFileImportError,
    DatasetFileNotFoundError,
    DatasetFileProcessingError,
    DatasetFileSizeMismatchError,
    DatasetFileStatusConflictError,
    DatasetFileValidationError,
    get_dataset_version_import_result,
    process_dataset_version_file,
    upload_dataset_version_file,
)
from app.schemas.dataset_version import (
    DatasetVersionCompleteRequest,
    DatasetVersionCreateRequest,
    DatasetVersionFailRequest,
    DatasetVersionListResponse,
    DatasetVersionResponse,
    DatasetVersionStatus,
)
from app.services.dataset_version_registry_service import (
    DatasetVersionChecksumConflictError,
    DatasetVersionDatasetError,
    DatasetVersionNotFoundError,
    DatasetVersionReferencePeriodError,
    DatasetVersionRegistryError,
    DatasetVersionStatusConflictError,
    complete_dataset_version_processing,
    create_dataset_version,
    fail_dataset_version_processing,
    get_dataset_version_record,
    list_dataset_version_records,
    start_dataset_version_processing,
)


router = APIRouter(
    prefix="/admin/dataset-versions",
    tags=["Administração de versões de datasets"],
)
AdminActor = Annotated[str, Depends(require_admin_api_key)]


def _raise_registry_error(error: DatasetVersionRegistryError) -> None:
    if isinstance(error, DatasetVersionNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DATASET_VERSION_NOT_FOUND", "message": str(error)},
        ) from error
    if isinstance(error, DatasetVersionChecksumConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "DATASET_VERSION_CHECKSUM_CONFLICT", "message": str(error)},
        ) from error
    if isinstance(error, DatasetVersionStatusConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "DATASET_VERSION_STATUS_CONFLICT", "message": str(error)},
        ) from error
    if isinstance(error, DatasetVersionDatasetError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "DATASET_VERSION_DATASET_INVALID", "message": str(error)},
        ) from error
    if isinstance(error, DatasetVersionReferencePeriodError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "DATASET_VERSION_PERIOD_INVALID", "message": str(error)},
        ) from error
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={"code": "DATASET_VERSION_INVALID", "message": str(error)},
    ) from error


def _raise_file_import_error(error: DatasetFileImportError) -> None:
    if isinstance(error, DatasetFileNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
        code = "DATASET_FILE_VERSION_NOT_FOUND"
    elif isinstance(
        error,
        (DatasetFileStatusConflictError, DatasetFileAlreadyUploadedError),
    ):
        status_code = status.HTTP_409_CONFLICT
        code = "DATASET_FILE_STATUS_CONFLICT"
    elif isinstance(error, DatasetFileChecksumMismatchError):
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
        code = "DATASET_FILE_CHECKSUM_MISMATCH"
    elif isinstance(error, DatasetFileSizeMismatchError):
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
        code = "DATASET_FILE_SIZE_MISMATCH"
    elif isinstance(error, DatasetFileProcessingError):
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
        code = "DATASET_FILE_PROCESSING_FAILED"
    elif isinstance(error, DatasetFileValidationError):
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
        code = "DATASET_FILE_INVALID"
    else:
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
        code = "DATASET_FILE_IMPORT_INVALID"
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": str(error)},
    ) from error


@router.post("", response_model=DatasetVersionResponse, status_code=201)
def create_registered_dataset_version(
    payload: DatasetVersionCreateRequest,
    session: DatabaseSession,
    actor: AdminActor,
) -> DatasetVersionResponse:
    try:
        return create_dataset_version(session, payload=payload, actor=actor)
    except DatasetVersionRegistryError as error:
        _raise_registry_error(error)
        raise AssertionError("unreachable")


@router.get("", response_model=DatasetVersionListResponse)
def list_registered_dataset_versions(
    session: DatabaseSession,
    _: AdminActor,
    dataset_id: UUID | None = Query(default=None),
    version_status: DatasetVersionStatus | None = Query(default=None, alias="status"),
    created_by: str | None = Query(default=None, min_length=1, max_length=100),
    checksum_sha256: str | None = Query(default=None, min_length=64, max_length=64),
    reference_from: date | None = Query(default=None),
    reference_until: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> DatasetVersionListResponse:
    try:
        total, items = list_dataset_version_records(
            session,
            dataset_id=str(dataset_id) if dataset_id else None,
            status=version_status,
            created_by=created_by,
            checksum_sha256=checksum_sha256,
            reference_from=reference_from,
            reference_until=reference_until,
            limit=limit,
            offset=offset,
        )
    except DatasetVersionRegistryError as error:
        _raise_registry_error(error)
        raise AssertionError("unreachable")
    return DatasetVersionListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get("/{dataset_version_id}", response_model=DatasetVersionResponse)
def get_registered_dataset_version(
    dataset_version_id: UUID,
    session: DatabaseSession,
    _: AdminActor,
) -> DatasetVersionResponse:
    try:
        return get_dataset_version_record(session, str(dataset_version_id))
    except DatasetVersionRegistryError as error:
        _raise_registry_error(error)
        raise AssertionError("unreachable")


@router.post("/{dataset_version_id}/processing", response_model=DatasetVersionResponse)
def start_registered_dataset_version_processing(
    dataset_version_id: UUID,
    session: DatabaseSession,
    actor: AdminActor,
) -> DatasetVersionResponse:
    try:
        return start_dataset_version_processing(
            session,
            dataset_version_id=str(dataset_version_id),
            actor=actor,
        )
    except DatasetVersionRegistryError as error:
        _raise_registry_error(error)
        raise AssertionError("unreachable")


@router.post("/{dataset_version_id}/complete", response_model=DatasetVersionResponse)
def complete_registered_dataset_version_processing(
    dataset_version_id: UUID,
    payload: DatasetVersionCompleteRequest,
    session: DatabaseSession,
    actor: AdminActor,
) -> DatasetVersionResponse:
    try:
        return complete_dataset_version_processing(
            session,
            dataset_version_id=str(dataset_version_id),
            payload=payload,
            actor=actor,
        )
    except DatasetVersionRegistryError as error:
        _raise_registry_error(error)
        raise AssertionError("unreachable")


@router.post("/{dataset_version_id}/fail", response_model=DatasetVersionResponse)
def fail_registered_dataset_version_processing(
    dataset_version_id: UUID,
    payload: DatasetVersionFailRequest,
    session: DatabaseSession,
    actor: AdminActor,
) -> DatasetVersionResponse:
    try:
        return fail_dataset_version_processing(
            session,
            dataset_version_id=str(dataset_version_id),
            payload=payload,
            actor=actor,
        )
    except DatasetVersionRegistryError as error:
        _raise_registry_error(error)
        raise AssertionError("unreachable")


@router.post(
    "/{dataset_version_id}/file",
    response_model=DatasetFileUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_registered_dataset_version_file(
    dataset_version_id: UUID,
    session: DatabaseSession,
    actor: AdminActor,
    file: UploadFile = File(...),
) -> DatasetFileUploadResponse:
    try:
        return await upload_dataset_version_file(
            session,
            dataset_version_id=str(dataset_version_id),
            upload=file,
            actor=actor,
        )
    except DatasetFileImportError as error:
        _raise_file_import_error(error)
        raise AssertionError("unreachable")


@router.post(
    "/{dataset_version_id}/process-file",
    response_model=DatasetFileImportResultResponse,
)
def process_registered_dataset_version_file(
    dataset_version_id: UUID,
    session: DatabaseSession,
    actor: AdminActor,
) -> DatasetFileImportResultResponse:
    try:
        return process_dataset_version_file(
            session,
            dataset_version_id=str(dataset_version_id),
            actor=actor,
        )
    except DatasetFileImportError as error:
        _raise_file_import_error(error)
        raise AssertionError("unreachable")


@router.get(
    "/{dataset_version_id}/import-result",
    response_model=DatasetFileImportResultResponse,
)
def get_registered_dataset_version_import_result(
    dataset_version_id: UUID,
    session: DatabaseSession,
    _: AdminActor,
) -> DatasetFileImportResultResponse:
    try:
        return get_dataset_version_import_result(
            session,
            dataset_version_id=str(dataset_version_id),
        )
    except DatasetFileImportError as error:
        _raise_file_import_error(error)
        raise AssertionError("unreachable")
