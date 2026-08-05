import json
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.dataset_version_model import DatasetVersionModel
from app.repositories.dataset_versions_sqlalchemy import (
    add_dataset_version,
    get_dataset_version,
    get_dataset_version_by_checksum,
    list_dataset_versions,
    next_dataset_version_number,
    save_dataset_version,
)
from app.repositories.datasets_sqlalchemy import get_dataset
from app.schemas.dataset_version import (
    DatasetVersionCompleteRequest,
    DatasetVersionCreateRequest,
    DatasetVersionFailRequest,
    DatasetVersionResponse,
    DatasetVersionStatus,
)


class DatasetVersionRegistryError(Exception):
    pass


class DatasetVersionNotFoundError(DatasetVersionRegistryError):
    pass


class DatasetVersionDatasetError(DatasetVersionRegistryError):
    pass


class DatasetVersionChecksumConflictError(DatasetVersionRegistryError):
    pass


class DatasetVersionStatusConflictError(DatasetVersionRegistryError):
    pass


class DatasetVersionReferencePeriodError(DatasetVersionRegistryError):
    pass


def _metadata_to_json(metadata: dict[str, Any]) -> str:
    try:
        return json.dumps(metadata, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError) as error:
        raise DatasetVersionRegistryError(
            "Metadados inválidos para serialização JSON."
        ) from error


def _validate_reference_period(
    reference_start: date | None,
    reference_end: date | None,
) -> None:
    if (
        reference_start is not None
        and reference_end is not None
        and reference_start > reference_end
    ):
        raise DatasetVersionReferencePeriodError(
            "A data inicial não pode ser posterior à data final."
        )


def _to_response(model: DatasetVersionModel) -> DatasetVersionResponse:
    return DatasetVersionResponse(
        dataset_version_id=model.dataset_version_id,
        dataset_id=model.dataset_id,
        version_number=model.version_number,
        file_name=model.file_name,
        storage_path=model.storage_path,
        checksum_sha256=model.checksum_sha256,
        file_size_bytes=model.file_size_bytes,
        mime_type=model.mime_type,
        reference_start=model.reference_start,
        reference_end=model.reference_end,
        record_count=model.record_count,
        status=DatasetVersionStatus(model.status),
        error_message=model.error_message,
        metadata=json.loads(model.metadata_json),
        processing_started_at=model.processing_started_at,
        completed_at=model.completed_at,
        created_by=model.created_by,
        updated_by=model.updated_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def create_dataset_version(
    session: Session,
    *,
    payload: DatasetVersionCreateRequest,
    actor: str,
) -> DatasetVersionResponse:
    dataset = get_dataset(session, payload.dataset_id)
    if dataset is None:
        raise DatasetVersionDatasetError("Dataset não encontrado.")
    if dataset.status != "ACTIVE":
        raise DatasetVersionDatasetError(
            "O dataset precisa estar ativo para receber uma nova versão."
        )

    checksum = payload.checksum_sha256.lower()
    if (
        get_dataset_version_by_checksum(
            session,
            dataset_id=payload.dataset_id,
            checksum_sha256=checksum,
        )
        is not None
    ):
        raise DatasetVersionChecksumConflictError(
            "Este arquivo já foi registrado para o dataset informado."
        )

    _validate_reference_period(payload.reference_start, payload.reference_end)
    model = DatasetVersionModel(
        dataset_version_id=str(uuid4()),
        dataset_id=payload.dataset_id,
        version_number=next_dataset_version_number(session, payload.dataset_id),
        file_name=payload.file_name,
        storage_path=payload.storage_path,
        checksum_sha256=checksum,
        file_size_bytes=payload.file_size_bytes,
        mime_type=payload.mime_type,
        reference_start=payload.reference_start,
        reference_end=payload.reference_end,
        status=DatasetVersionStatus.REGISTERED.value,
        metadata_json=_metadata_to_json(payload.metadata),
        created_by=actor,
        updated_by=actor,
    )
    try:
        return _to_response(add_dataset_version(session, model))
    except IntegrityError as error:
        session.rollback()
        raise DatasetVersionChecksumConflictError(
            "Não foi possível registrar a versão por conflito de versão ou checksum."
        ) from error


def get_dataset_version_record(
    session: Session,
    dataset_version_id: str,
) -> DatasetVersionResponse:
    model = get_dataset_version(session, dataset_version_id)
    if model is None:
        raise DatasetVersionNotFoundError("Versão de dataset não encontrada.")
    return _to_response(model)


def list_dataset_version_records(
    session: Session,
    *,
    dataset_id: str | None,
    status: DatasetVersionStatus | None,
    created_by: str | None,
    checksum_sha256: str | None,
    reference_from: date | None,
    reference_until: date | None,
    limit: int,
    offset: int,
) -> tuple[int, list[DatasetVersionResponse]]:
    _validate_reference_period(reference_from, reference_until)
    checksum = checksum_sha256.lower() if checksum_sha256 else None
    total, models = list_dataset_versions(
        session,
        dataset_id=dataset_id,
        status=status.value if status else None,
        created_by=created_by,
        checksum_sha256=checksum,
        reference_from=reference_from,
        reference_until=reference_until,
        limit=limit,
        offset=offset,
    )
    return total, [_to_response(model) for model in models]


def start_dataset_version_processing(
    session: Session,
    *,
    dataset_version_id: str,
    actor: str,
) -> DatasetVersionResponse:
    model = get_dataset_version(session, dataset_version_id)
    if model is None:
        raise DatasetVersionNotFoundError("Versão de dataset não encontrada.")
    if model.status != DatasetVersionStatus.REGISTERED.value:
        raise DatasetVersionStatusConflictError(
            "Somente versões registradas podem iniciar processamento."
        )
    model.status = DatasetVersionStatus.PROCESSING.value
    model.processing_started_at = datetime.now(timezone.utc)
    model.error_message = None
    model.updated_by = actor
    return _to_response(save_dataset_version(session, model))


def complete_dataset_version_processing(
    session: Session,
    *,
    dataset_version_id: str,
    payload: DatasetVersionCompleteRequest,
    actor: str,
) -> DatasetVersionResponse:
    model = get_dataset_version(session, dataset_version_id)
    if model is None:
        raise DatasetVersionNotFoundError("Versão de dataset não encontrada.")
    if model.status != DatasetVersionStatus.PROCESSING.value:
        raise DatasetVersionStatusConflictError(
            "Somente versões em processamento podem ser concluídas."
        )
    model.status = DatasetVersionStatus.COMPLETED.value
    model.record_count = payload.record_count
    model.completed_at = datetime.now(timezone.utc)
    model.error_message = None
    if payload.metadata is not None:
        model.metadata_json = _metadata_to_json(payload.metadata)
    model.updated_by = actor
    return _to_response(save_dataset_version(session, model))


def fail_dataset_version_processing(
    session: Session,
    *,
    dataset_version_id: str,
    payload: DatasetVersionFailRequest,
    actor: str,
) -> DatasetVersionResponse:
    model = get_dataset_version(session, dataset_version_id)
    if model is None:
        raise DatasetVersionNotFoundError("Versão de dataset não encontrada.")
    if model.status != DatasetVersionStatus.PROCESSING.value:
        raise DatasetVersionStatusConflictError(
            "Somente versões em processamento podem falhar."
        )
    model.status = DatasetVersionStatus.FAILED.value
    model.error_message = payload.error_message
    model.completed_at = datetime.now(timezone.utc)
    model.updated_by = actor
    return _to_response(save_dataset_version(session, model))
