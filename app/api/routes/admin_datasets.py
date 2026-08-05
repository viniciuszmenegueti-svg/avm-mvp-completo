from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.admin_auth import require_admin_api_key
from app.infrastructure.dependencies import DatabaseSession
from app.schemas.dataset import (
    DatasetCreateRequest,
    DatasetListResponse,
    DatasetResponse,
    DatasetStatus,
    DatasetUpdateRequest,
)
from app.services.dataset_registry_service import (
    DatasetDataSourceError,
    DatasetNameConflictError,
    DatasetNotFoundError,
    DatasetReferencePeriodError,
    DatasetRegistryError,
    DatasetStatusConflictError,
    change_dataset_status,
    create_dataset,
    get_dataset_record,
    list_dataset_records,
    update_dataset,
)


router = APIRouter(prefix="/admin/datasets", tags=["Administração de datasets"])
AdminActor = Annotated[str, Depends(require_admin_api_key)]


def _raise_registry_error(error: DatasetRegistryError) -> None:
    if isinstance(error, DatasetNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DATASET_NOT_FOUND", "message": str(error)},
        ) from error
    if isinstance(error, DatasetNameConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "DATASET_NAME_CONFLICT", "message": str(error)},
        ) from error
    if isinstance(error, DatasetStatusConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "DATASET_STATUS_CONFLICT", "message": str(error)},
        ) from error
    if isinstance(error, DatasetDataSourceError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "DATASET_DATA_SOURCE_INVALID", "message": str(error)},
        ) from error
    if isinstance(error, DatasetReferencePeriodError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "DATASET_REFERENCE_PERIOD_INVALID", "message": str(error)},
        ) from error
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={"code": "DATASET_INVALID", "message": str(error)},
    ) from error


@router.post("", response_model=DatasetResponse, status_code=201, summary="Cadastra um dataset")
def create_registered_dataset(
    payload: DatasetCreateRequest,
    session: DatabaseSession,
    actor: AdminActor,
) -> DatasetResponse:
    try:
        return create_dataset(session, payload=payload, actor=actor)
    except DatasetRegistryError as error:
        _raise_registry_error(error)
        raise AssertionError("unreachable")


@router.get("", response_model=DatasetListResponse, summary="Lista datasets cadastrados")
def list_registered_datasets(
    session: DatabaseSession,
    _: AdminActor,
    data_source_id: UUID | None = Query(default=None),
    dataset_status: DatasetStatus | None = Query(default=None, alias="status"),
    name: str | None = Query(default=None, min_length=1, max_length=150),
    reference_from: date | None = Query(default=None),
    reference_until: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> DatasetListResponse:
    try:
        total, items = list_dataset_records(
            session,
            data_source_id=str(data_source_id) if data_source_id else None,
            status=dataset_status,
            name=name,
            reference_from=reference_from,
            reference_until=reference_until,
            limit=limit,
            offset=offset,
        )
    except DatasetRegistryError as error:
        _raise_registry_error(error)
        raise AssertionError("unreachable")
    return DatasetListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get("/{dataset_id}", response_model=DatasetResponse, summary="Consulta um dataset")
def get_registered_dataset(
    dataset_id: UUID,
    session: DatabaseSession,
    _: AdminActor,
) -> DatasetResponse:
    try:
        return get_dataset_record(session, str(dataset_id))
    except DatasetRegistryError as error:
        _raise_registry_error(error)
        raise AssertionError("unreachable")


@router.patch("/{dataset_id}", response_model=DatasetResponse, summary="Atualiza um dataset")
def update_registered_dataset(
    dataset_id: UUID,
    payload: DatasetUpdateRequest,
    session: DatabaseSession,
    actor: AdminActor,
) -> DatasetResponse:
    try:
        return update_dataset(
            session,
            dataset_id=str(dataset_id),
            payload=payload,
            actor=actor,
        )
    except DatasetRegistryError as error:
        _raise_registry_error(error)
        raise AssertionError("unreachable")


@router.post("/{dataset_id}/activate", response_model=DatasetResponse, summary="Ativa um dataset")
def activate_registered_dataset(
    dataset_id: UUID,
    session: DatabaseSession,
    actor: AdminActor,
) -> DatasetResponse:
    try:
        return change_dataset_status(
            session,
            dataset_id=str(dataset_id),
            target_status=DatasetStatus.ACTIVE,
            actor=actor,
        )
    except DatasetRegistryError as error:
        _raise_registry_error(error)
        raise AssertionError("unreachable")


@router.post("/{dataset_id}/deactivate", response_model=DatasetResponse, summary="Inativa um dataset")
def deactivate_registered_dataset(
    dataset_id: UUID,
    session: DatabaseSession,
    actor: AdminActor,
) -> DatasetResponse:
    try:
        return change_dataset_status(
            session,
            dataset_id=str(dataset_id),
            target_status=DatasetStatus.INACTIVE,
            actor=actor,
        )
    except DatasetRegistryError as error:
        _raise_registry_error(error)
        raise AssertionError("unreachable")


@router.post("/{dataset_id}/archive", response_model=DatasetResponse, summary="Arquiva um dataset")
def archive_registered_dataset(
    dataset_id: UUID,
    session: DatabaseSession,
    actor: AdminActor,
) -> DatasetResponse:
    try:
        return change_dataset_status(
            session,
            dataset_id=str(dataset_id),
            target_status=DatasetStatus.ARCHIVED,
            actor=actor,
        )
    except DatasetRegistryError as error:
        _raise_registry_error(error)
        raise AssertionError("unreachable")
