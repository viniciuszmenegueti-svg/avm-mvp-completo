from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.admin_auth import require_admin_api_key
from app.infrastructure.dependencies import DatabaseSession
from app.schemas.data_source import (
    DataSourceCreateRequest,
    DataSourceListResponse,
    DataSourceResponse,
    DataSourceStatus,
    DataSourceUpdateRequest,
)
from app.services.data_source_registry_service import (
    DataSourceNameConflictError,
    DataSourceNotFoundError,
    DataSourceRegistryError,
    DataSourceStatusConflictError,
    change_data_source_status,
    create_data_source,
    get_data_source_record,
    list_data_source_records,
    update_data_source,
)


router = APIRouter(prefix="/admin/data-sources", tags=["Administração de fontes"])
AdminActor = Annotated[str, Depends(require_admin_api_key)]


def _raise_registry_error(error: DataSourceRegistryError) -> None:
    if isinstance(error, DataSourceNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DATA_SOURCE_NOT_FOUND", "message": str(error)},
        ) from error
    if isinstance(error, (DataSourceNameConflictError, DataSourceStatusConflictError)):
        code = (
            "DATA_SOURCE_NAME_CONFLICT"
            if isinstance(error, DataSourceNameConflictError)
            else "DATA_SOURCE_STATUS_CONFLICT"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": code, "message": str(error)},
        ) from error
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={"code": "DATA_SOURCE_INVALID", "message": str(error)},
    ) from error


@router.post(
    "",
    response_model=DataSourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra uma fonte de dados",
)
def create_registered_data_source(
    payload: DataSourceCreateRequest,
    session: DatabaseSession,
    actor: AdminActor,
) -> DataSourceResponse:
    try:
        return create_data_source(session, payload=payload, actor=actor)
    except DataSourceRegistryError as error:
        _raise_registry_error(error)
        raise AssertionError("unreachable")


@router.get(
    "",
    response_model=DataSourceListResponse,
    summary="Lista fontes de dados cadastradas",
)
def list_registered_data_sources(
    session: DatabaseSession,
    _: AdminActor,
    data_source_status: DataSourceStatus | None = Query(default=None, alias="status"),
    source_type: str | None = Query(default=None, min_length=1, max_length=50),
    responsible: str | None = Query(default=None, min_length=1, max_length=120),
    name: str | None = Query(default=None, min_length=1, max_length=150),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> DataSourceListResponse:
    total, items = list_data_source_records(
        session,
        status=data_source_status,
        source_type=source_type,
        responsible=responsible,
        name=name,
        limit=limit,
        offset=offset,
    )
    return DataSourceListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get(
    "/{data_source_id}",
    response_model=DataSourceResponse,
    summary="Consulta uma fonte de dados",
)
def get_registered_data_source(
    data_source_id: UUID,
    session: DatabaseSession,
    _: AdminActor,
) -> DataSourceResponse:
    try:
        return get_data_source_record(session, str(data_source_id))
    except DataSourceRegistryError as error:
        _raise_registry_error(error)
        raise AssertionError("unreachable")


@router.patch(
    "/{data_source_id}",
    response_model=DataSourceResponse,
    summary="Atualiza uma fonte de dados",
)
def update_registered_data_source(
    data_source_id: UUID,
    payload: DataSourceUpdateRequest,
    session: DatabaseSession,
    actor: AdminActor,
) -> DataSourceResponse:
    try:
        return update_data_source(
            session, data_source_id=str(data_source_id), payload=payload, actor=actor
        )
    except DataSourceRegistryError as error:
        _raise_registry_error(error)
        raise AssertionError("unreachable")


@router.post(
    "/{data_source_id}/activate",
    response_model=DataSourceResponse,
    summary="Ativa uma fonte de dados",
)
def activate_registered_data_source(
    data_source_id: UUID,
    session: DatabaseSession,
    actor: AdminActor,
) -> DataSourceResponse:
    try:
        return change_data_source_status(
            session,
            data_source_id=str(data_source_id),
            target_status=DataSourceStatus.ACTIVE,
            actor=actor,
        )
    except DataSourceRegistryError as error:
        _raise_registry_error(error)
        raise AssertionError("unreachable")


@router.post(
    "/{data_source_id}/deactivate",
    response_model=DataSourceResponse,
    summary="Inativa uma fonte de dados",
)
def deactivate_registered_data_source(
    data_source_id: UUID,
    session: DatabaseSession,
    actor: AdminActor,
) -> DataSourceResponse:
    try:
        return change_data_source_status(
            session,
            data_source_id=str(data_source_id),
            target_status=DataSourceStatus.INACTIVE,
            actor=actor,
        )
    except DataSourceRegistryError as error:
        _raise_registry_error(error)
        raise AssertionError("unreachable")
