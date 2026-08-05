import json
from datetime import date
from typing import Any
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.dataset_model import DatasetModel
from app.repositories.data_sources_sqlalchemy import get_data_source
from app.repositories.datasets_sqlalchemy import (
    add_dataset,
    get_dataset,
    get_dataset_by_source_and_name_key,
    list_datasets,
    save_dataset,
)
from app.schemas.dataset import (
    DatasetCreateRequest,
    DatasetResponse,
    DatasetStatus,
    DatasetUpdateRequest,
)


class DatasetRegistryError(Exception):
    pass


class DatasetNotFoundError(DatasetRegistryError):
    pass


class DatasetNameConflictError(DatasetRegistryError):
    pass


class DatasetStatusConflictError(DatasetRegistryError):
    pass


class DatasetDataSourceError(DatasetRegistryError):
    pass


class DatasetReferencePeriodError(DatasetRegistryError):
    pass


def normalize_name_key(name: str) -> str:
    return " ".join(name.casefold().split())


def _metadata_to_json(metadata: dict[str, Any]) -> str:
    try:
        return json.dumps(metadata, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError) as error:
        raise DatasetRegistryError("Metadados inválidos para serialização JSON.") from error


def _validate_reference_period(
    reference_start: date | None,
    reference_end: date | None,
) -> None:
    if (
        reference_start is not None
        and reference_end is not None
        and reference_start > reference_end
    ):
        raise DatasetReferencePeriodError(
            "A data inicial não pode ser posterior à data final."
        )


def _to_response(model: DatasetModel) -> DatasetResponse:
    return DatasetResponse(
        dataset_id=model.dataset_id,
        data_source_id=model.data_source_id,
        name=model.name,
        description=model.description,
        reference_start=model.reference_start,
        reference_end=model.reference_end,
        metadata=json.loads(model.metadata_json),
        status=DatasetStatus(model.status),
        created_by=model.created_by,
        updated_by=model.updated_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def create_dataset(
    session: Session,
    *,
    payload: DatasetCreateRequest,
    actor: str,
) -> DatasetResponse:
    source = get_data_source(session, payload.data_source_id)
    if source is None:
        raise DatasetDataSourceError("Fonte de dados não encontrada.")
    if source.status != "ACTIVE":
        raise DatasetDataSourceError("A fonte de dados precisa estar ativa.")

    name_key = normalize_name_key(payload.name)
    if (
        get_dataset_by_source_and_name_key(
            session,
            data_source_id=payload.data_source_id,
            name_key=name_key,
        )
        is not None
    ):
        raise DatasetNameConflictError(
            "Já existe um dataset com este nome para a fonte informada."
        )

    model = DatasetModel(
        dataset_id=str(uuid4()),
        data_source_id=payload.data_source_id,
        name=payload.name,
        name_key=name_key,
        description=payload.description,
        reference_start=payload.reference_start,
        reference_end=payload.reference_end,
        metadata_json=_metadata_to_json(payload.metadata),
        status=DatasetStatus.ACTIVE.value,
        created_by=actor,
        updated_by=actor,
    )
    try:
        return _to_response(add_dataset(session, model))
    except IntegrityError as error:
        session.rollback()
        raise DatasetNameConflictError(
            "Já existe um dataset com este nome para a fonte informada."
        ) from error


def get_dataset_record(session: Session, dataset_id: str) -> DatasetResponse:
    model = get_dataset(session, dataset_id)
    if model is None:
        raise DatasetNotFoundError("Dataset não encontrado.")
    return _to_response(model)


def list_dataset_records(
    session: Session,
    *,
    data_source_id: str | None,
    status: DatasetStatus | None,
    name: str | None,
    reference_from: date | None,
    reference_until: date | None,
    limit: int,
    offset: int,
) -> tuple[int, list[DatasetResponse]]:
    _validate_reference_period(reference_from, reference_until)
    total, models = list_datasets(
        session,
        data_source_id=data_source_id,
        status=status.value if status else None,
        name=name,
        reference_from=reference_from,
        reference_until=reference_until,
        limit=limit,
        offset=offset,
    )
    return total, [_to_response(model) for model in models]


def update_dataset(
    session: Session,
    *,
    dataset_id: str,
    payload: DatasetUpdateRequest,
    actor: str,
) -> DatasetResponse:
    model = get_dataset(session, dataset_id)
    if model is None:
        raise DatasetNotFoundError("Dataset não encontrado.")
    if model.status == DatasetStatus.ARCHIVED.value:
        raise DatasetStatusConflictError("Dataset arquivado não pode ser alterado.")

    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes:
        name = changes["name"]
        name_key = normalize_name_key(name)
        existing = get_dataset_by_source_and_name_key(
            session,
            data_source_id=model.data_source_id,
            name_key=name_key,
        )
        if existing is not None and existing.dataset_id != dataset_id:
            raise DatasetNameConflictError(
                "Já existe um dataset com este nome para a fonte informada."
            )
        model.name = name
        model.name_key = name_key
    if "description" in changes:
        model.description = changes["description"]
    if "reference_start" in changes:
        model.reference_start = changes["reference_start"]
    if "reference_end" in changes:
        model.reference_end = changes["reference_end"]
    if "metadata" in changes:
        model.metadata_json = _metadata_to_json(changes["metadata"])

    _validate_reference_period(model.reference_start, model.reference_end)
    model.updated_by = actor

    try:
        return _to_response(save_dataset(session, model))
    except IntegrityError as error:
        session.rollback()
        raise DatasetNameConflictError(
            "Já existe um dataset com este nome para a fonte informada."
        ) from error


def change_dataset_status(
    session: Session,
    *,
    dataset_id: str,
    target_status: DatasetStatus,
    actor: str,
) -> DatasetResponse:
    model = get_dataset(session, dataset_id)
    if model is None:
        raise DatasetNotFoundError("Dataset não encontrado.")
    if model.status == target_status.value:
        raise DatasetStatusConflictError(
            f"O dataset já está com status {target_status.value}."
        )
    if model.status == DatasetStatus.ARCHIVED.value:
        raise DatasetStatusConflictError("Dataset arquivado não pode mudar de status.")

    model.status = target_status.value
    model.updated_by = actor
    return _to_response(save_dataset(session, model))
