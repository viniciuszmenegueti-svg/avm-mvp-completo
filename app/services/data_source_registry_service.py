import json
from typing import Any
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.data_source_model import DataSourceModel
from app.repositories.data_sources_sqlalchemy import (
    add_data_source,
    get_data_source,
    get_data_source_by_name_key,
    list_data_sources,
    save_data_source,
)
from app.schemas.data_source import (
    DataSourceCreateRequest,
    DataSourceResponse,
    DataSourceStatus,
    DataSourceUpdateRequest,
)


class DataSourceRegistryError(Exception):
    pass


class DataSourceNotFoundError(DataSourceRegistryError):
    pass


class DataSourceNameConflictError(DataSourceRegistryError):
    pass


class DataSourceStatusConflictError(DataSourceRegistryError):
    pass


def normalize_name_key(name: str) -> str:
    return " ".join(name.casefold().split())


def _metadata_to_json(metadata: dict[str, Any]) -> str:
    try:
        return json.dumps(metadata, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError) as error:
        raise DataSourceRegistryError("Metadados inválidos para serialização JSON.") from error


def _to_response(model: DataSourceModel) -> DataSourceResponse:
    return DataSourceResponse(
        data_source_id=model.data_source_id,
        name=model.name,
        source_type=model.source_type,
        responsible=model.responsible,
        description=model.description,
        reference_date=model.reference_date,
        metadata=json.loads(model.metadata_json),
        status=DataSourceStatus(model.status),
        created_by=model.created_by,
        updated_by=model.updated_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def create_data_source(
    session: Session, *, payload: DataSourceCreateRequest, actor: str
) -> DataSourceResponse:
    name_key = normalize_name_key(payload.name)
    if get_data_source_by_name_key(session, name_key) is not None:
        raise DataSourceNameConflictError("Já existe uma fonte com este nome.")

    model = DataSourceModel(
        data_source_id=str(uuid4()),
        name=payload.name,
        name_key=name_key,
        source_type=payload.source_type.upper(),
        responsible=payload.responsible,
        description=payload.description,
        reference_date=payload.reference_date,
        metadata_json=_metadata_to_json(payload.metadata),
        status=DataSourceStatus.ACTIVE.value,
        created_by=actor,
        updated_by=actor,
    )
    try:
        return _to_response(add_data_source(session, model))
    except IntegrityError as error:
        session.rollback()
        raise DataSourceNameConflictError("Já existe uma fonte com este nome.") from error


def get_data_source_record(session: Session, data_source_id: str) -> DataSourceResponse:
    model = get_data_source(session, data_source_id)
    if model is None:
        raise DataSourceNotFoundError("Fonte de dados não encontrada.")
    return _to_response(model)


def list_data_source_records(
    session: Session,
    *,
    status: DataSourceStatus | None,
    source_type: str | None,
    responsible: str | None,
    name: str | None,
    limit: int,
    offset: int,
) -> tuple[int, list[DataSourceResponse]]:
    total, models = list_data_sources(
        session,
        status=status.value if status else None,
        source_type=source_type,
        responsible=responsible,
        name=name,
        limit=limit,
        offset=offset,
    )
    return total, [_to_response(model) for model in models]


def update_data_source(
    session: Session,
    *,
    data_source_id: str,
    payload: DataSourceUpdateRequest,
    actor: str,
) -> DataSourceResponse:
    model = get_data_source(session, data_source_id)
    if model is None:
        raise DataSourceNotFoundError("Fonte de dados não encontrada.")

    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes:
        name = changes["name"]
        name_key = normalize_name_key(name)
        existing = get_data_source_by_name_key(session, name_key)
        if existing is not None and existing.data_source_id != data_source_id:
            raise DataSourceNameConflictError("Já existe uma fonte com este nome.")
        model.name = name
        model.name_key = name_key
    if "source_type" in changes:
        model.source_type = changes["source_type"].upper()
    if "responsible" in changes:
        model.responsible = changes["responsible"]
    if "description" in changes:
        model.description = changes["description"]
    if "reference_date" in changes:
        model.reference_date = changes["reference_date"]
    if "metadata" in changes:
        model.metadata_json = _metadata_to_json(changes["metadata"])
    model.updated_by = actor

    try:
        return _to_response(save_data_source(session, model))
    except IntegrityError as error:
        session.rollback()
        raise DataSourceNameConflictError("Já existe uma fonte com este nome.") from error


def change_data_source_status(
    session: Session,
    *,
    data_source_id: str,
    target_status: DataSourceStatus,
    actor: str,
) -> DataSourceResponse:
    model = get_data_source(session, data_source_id)
    if model is None:
        raise DataSourceNotFoundError("Fonte de dados não encontrada.")
    if model.status == target_status.value:
        raise DataSourceStatusConflictError(
            f"A fonte já está com status {target_status.value}."
        )
    model.status = target_status.value
    model.updated_by = actor
    return _to_response(save_data_source(session, model))
