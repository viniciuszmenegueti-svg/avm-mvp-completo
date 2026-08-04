from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.cnefe_address_model import CnefeAddressModel
from app.domain.cnefe_import_model import CnefeImportModel, CnefeImportStatus


def start_cnefe_import(
    session: Session,
    *,
    dataset_version: str,
    source_file_sha256: str,
    source_filename: str,
    city_ibge_code: str,
    state: str,
) -> CnefeImportModel:
    registry = CnefeImportModel(
        import_id=str(uuid4()),
        dataset_version=dataset_version,
        source_file_sha256=source_file_sha256,
        source_filename=source_filename,
        city_ibge_code=city_ibge_code,
        state=state,
        status=CnefeImportStatus.LOADING.value,
        record_count=0,
    )
    session.add(registry)
    session.commit()
    session.refresh(registry)
    return registry


def update_cnefe_import_count(session: Session, import_id: str) -> int:
    registry = session.get(CnefeImportModel, import_id)
    if registry is None:
        raise ValueError("Importação CNEFE não encontrada.")
    count_statement = (
        select(func.count())
        .select_from(CnefeAddressModel)
        .where(CnefeAddressModel.import_id == import_id)
    )
    registry.record_count = int(session.scalar(count_statement) or 0)
    session.commit()
    return registry.record_count


def activate_cnefe_import(session: Session, import_id: str) -> CnefeImportModel:
    registry = session.get(CnefeImportModel, import_id)
    if registry is None:
        raise ValueError("Importação CNEFE não encontrada.")
    if registry.status != CnefeImportStatus.LOADING.value:
        raise ValueError("Somente uma importação LOADING pode ser ativada.")

    count_statement = (
        select(func.count())
        .select_from(CnefeAddressModel)
        .where(CnefeAddressModel.import_id == import_id)
    )
    registry.record_count = int(session.scalar(count_statement) or 0)
    if registry.record_count == 0:
        raise ValueError("Uma importação CNEFE vazia não pode ser ativada.")
    now = datetime.now(timezone.utc)
    registry.status = CnefeImportStatus.ACTIVE.value
    registry.completed_at = now
    registry.activated_at = now
    registry.failure_reason = None
    session.commit()
    session.refresh(registry)
    return registry


def fail_cnefe_import(
    session: Session,
    import_id: str,
    error: Exception,
) -> CnefeImportModel:
    registry = session.get(CnefeImportModel, import_id)
    if registry is None:
        raise ValueError("Importação CNEFE não encontrada.")

    count_statement = (
        select(func.count())
        .select_from(CnefeAddressModel)
        .where(CnefeAddressModel.import_id == import_id)
    )
    registry.record_count = int(session.scalar(count_statement) or 0)
    registry.status = CnefeImportStatus.FAILED.value
    registry.completed_at = datetime.now(timezone.utc)
    registry.activated_at = None
    registry.failure_reason = str(error)[:2000]
    session.commit()
    session.refresh(registry)
    return registry
