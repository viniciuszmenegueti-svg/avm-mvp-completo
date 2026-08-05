import csv
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.dataset_import_staging_model import (
    DatasetImportExecutionModel,
    DatasetImportRowModel,
)
from app.repositories.dataset_import_staging_sqlalchemy import (
    add_execution,
    add_rows,
    delete_staging_for_version,
    get_latest_execution,
    get_running_execution,
    list_rejected_rows,
    save_execution,
)
from app.repositories.dataset_versions_sqlalchemy import get_dataset_version
from app.schemas.dataset_import_staging import (
    DatasetImportFieldType,
    DatasetImportRejectedRowResponse,
    DatasetImportRejectedRowsListResponse,
    DatasetImportRowStatus,
    DatasetImportStagingRequest,
    DatasetImportStagingSummaryResponse,
)
from app.schemas.dataset_version import DatasetVersionStatus


class DatasetImportStagingError(Exception):
    pass


class DatasetImportStagingNotFoundError(DatasetImportStagingError):
    pass


class DatasetImportStagingConflictError(DatasetImportStagingError):
    pass


class DatasetImportStagingValidationError(DatasetImportStagingError):
    pass


_TRUE_VALUES = {"1", "true", "t", "yes", "y", "sim", "s"}
_FALSE_VALUES = {"0", "false", "f", "no", "n", "nao", "não"}
_SPACE_RE = re.compile(r"\s+")


def _storage_root() -> Path:
    configured = os.getenv("DATASET_UPLOAD_DIR", "data/dataset-files")
    root = Path(configured)
    if not root.is_absolute():
        root = Path(__file__).resolve().parents[2] / root
    return root.resolve()


def _dataset_file_path(storage_path: str) -> Path:
    root = _storage_root()
    path = (root / storage_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise DatasetImportStagingValidationError(
            "O caminho do arquivo está fora do diretório permitido."
        ) from error
    return path


def _load_import_metadata(metadata_json: str) -> tuple[str, str]:
    try:
        metadata = json.loads(metadata_json)
    except (TypeError, json.JSONDecodeError):
        metadata = {}
    import_metadata = metadata.get("file_import", {}) if isinstance(metadata, dict) else {}
    delimiter = import_metadata.get("delimiter", ",")
    encoding = import_metadata.get("encoding", "utf-8")
    if delimiter not in {",", ";", "\t", "|"}:
        delimiter = ","
    if encoding not in {"utf-8", "utf-8-sig"}:
        encoding = "utf-8"
    return delimiter, encoding


def _normalize_string(value: str) -> str:
    return _SPACE_RE.sub(" ", value.strip())


def _normalize_value(
    value: str,
    field_type: DatasetImportFieldType,
    date_format: str,
) -> tuple[Any, str | None]:
    text = _normalize_string(value)
    if field_type == DatasetImportFieldType.STRING:
        return text, None
    if not text:
        return None, None
    if field_type == DatasetImportFieldType.INTEGER:
        try:
            return int(text), None
        except ValueError:
            return None, "valor inteiro inválido"
    if field_type == DatasetImportFieldType.DECIMAL:
        normalized = text.replace(" ", "").replace(",", ".")
        try:
            return format(Decimal(normalized), "f"), None
        except InvalidOperation:
            return None, "valor decimal inválido"
    if field_type == DatasetImportFieldType.DATE:
        try:
            return datetime.strptime(text, date_format).date().isoformat(), None
        except ValueError:
            return None, f"data inválida; formato esperado {date_format}"
    if field_type == DatasetImportFieldType.BOOLEAN:
        key = text.casefold()
        if key in _TRUE_VALUES:
            return True, None
        if key in _FALSE_VALUES:
            return False, None
        return None, "valor booleano inválido"
    return text, None


def _schema_payload(payload: DatasetImportStagingRequest) -> dict[str, Any]:
    return {
        "required_fields": payload.required_fields,
        "field_types": {key: value.value for key, value in payload.field_types.items()},
        "date_format": payload.date_format,
        "batch_size": payload.batch_size,
    }


def _summary(model: DatasetImportExecutionModel) -> DatasetImportStagingSummaryResponse:
    try:
        schema = json.loads(model.schema_json)
    except json.JSONDecodeError:
        schema = {}
    return DatasetImportStagingSummaryResponse(
        execution_id=model.execution_id,
        dataset_version_id=model.dataset_version_id,
        status=model.status,
        total_rows=model.total_rows,
        valid_rows=model.valid_rows,
        invalid_rows=model.invalid_rows,
        duplicate_rows=model.duplicate_rows,
        validation_schema=schema if isinstance(schema, dict) else {},
        error_message=model.error_message,
        started_at=model.started_at,
        completed_at=model.completed_at,
        created_by=model.created_by,
        created_at=model.created_at,
    )


def _row_response(model: DatasetImportRowModel) -> DatasetImportRejectedRowResponse:
    return DatasetImportRejectedRowResponse(
        row_id=model.row_id,
        execution_id=model.execution_id,
        dataset_version_id=model.dataset_version_id,
        line_number=model.line_number,
        status=model.status,
        original=json.loads(model.original_json),
        normalized=(
            json.loads(model.normalized_json)
            if model.normalized_json is not None
            else None
        ),
        errors=json.loads(model.errors_json),
        row_hash=model.row_hash,
        created_at=model.created_at,
    )


def stage_dataset_version_file(
    session: Session,
    *,
    dataset_version_id: str,
    payload: DatasetImportStagingRequest,
    actor: str,
) -> DatasetImportStagingSummaryResponse:
    version = get_dataset_version(session, dataset_version_id)
    if version is None:
        raise DatasetImportStagingNotFoundError("Versão de dataset não encontrada.")
    if version.status != DatasetVersionStatus.COMPLETED.value:
        raise DatasetImportStagingConflictError(
            "O staging exige uma versão com processamento de arquivo concluído."
        )
    running = get_running_execution(session, dataset_version_id)
    if running is not None:
        raise DatasetImportStagingConflictError(
            "Já existe uma execução de staging em andamento para esta versão."
        )
    latest = get_latest_execution(session, dataset_version_id)
    if latest is not None and not payload.force_reprocess:
        raise DatasetImportStagingConflictError(
            "A versão já possui staging. Use force_reprocess para substituir."
        )
    if latest is not None:
        delete_staging_for_version(session, dataset_version_id)

    path = _dataset_file_path(version.storage_path)
    if not path.is_file():
        raise DatasetImportStagingValidationError(
            "O arquivo da versão não foi encontrado no armazenamento."
        )

    started_at = datetime.now(timezone.utc)
    execution = DatasetImportExecutionModel(
        execution_id=str(uuid4()),
        dataset_version_id=dataset_version_id,
        status="RUNNING",
        schema_json=json.dumps(_schema_payload(payload), ensure_ascii=False, sort_keys=True),
        started_at=started_at,
        created_by=actor,
    )
    add_execution(session, execution)

    delimiter, encoding = _load_import_metadata(version.metadata_json)
    required_lookup = {item.casefold(): item for item in payload.required_fields}
    type_lookup = {key.casefold(): value for key, value in payload.field_types.items()}
    seen_hashes: set[str] = set()
    batch: list[DatasetImportRowModel] = []

    try:
        with path.open("r", encoding=encoding, newline="") as stream:
            reader = csv.DictReader(stream, delimiter=delimiter)
            if reader.fieldnames is None:
                raise DatasetImportStagingValidationError("O CSV não possui cabeçalho.")
            headers = [header.strip() for header in reader.fieldnames]
            header_lookup = {header.casefold(): header for header in headers}
            missing_schema_fields = sorted(
                name for key, name in required_lookup.items() if key not in header_lookup
            )
            missing_schema_fields.extend(
                key for key in payload.field_types if key.casefold() not in header_lookup
            )
            if missing_schema_fields:
                raise DatasetImportStagingValidationError(
                    "Campos configurados ausentes no CSV: "
                    + ", ".join(sorted(set(missing_schema_fields)))
                )

            for line_number, raw_row in enumerate(reader, start=2):
                if raw_row is None or all(
                    value is None or not str(value).strip() for value in raw_row.values()
                ):
                    continue
                original = {
                    (key.strip() if key is not None else ""): (value or "")
                    for key, value in raw_row.items()
                }
                normalized: dict[str, Any] = {}
                errors: list[str] = []

                for header in headers:
                    raw_value = original.get(header, "")
                    field_type = type_lookup.get(
                        header.casefold(), DatasetImportFieldType.STRING
                    )
                    normalized_value, type_error = _normalize_value(
                        raw_value, field_type, payload.date_format
                    )
                    normalized[header] = normalized_value
                    if type_error is not None:
                        errors.append(f"{header}: {type_error}")

                for key, configured_name in required_lookup.items():
                    header = header_lookup[key]
                    value = normalized.get(header)
                    if value is None or (isinstance(value, str) and not value.strip()):
                        errors.append(f"{configured_name}: campo obrigatório")

                row_hash = hashlib.sha256(
                    json.dumps(
                        normalized,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest()

                if errors:
                    row_status = DatasetImportRowStatus.INVALID.value
                    execution.invalid_rows += 1
                elif row_hash in seen_hashes:
                    row_status = DatasetImportRowStatus.DUPLICATE.value
                    errors.append("Linha duplicada dentro do arquivo.")
                    execution.duplicate_rows += 1
                else:
                    row_status = DatasetImportRowStatus.VALID.value
                    execution.valid_rows += 1
                    seen_hashes.add(row_hash)

                execution.total_rows += 1
                batch.append(
                    DatasetImportRowModel(
                        row_id=str(uuid4()),
                        execution_id=execution.execution_id,
                        dataset_version_id=dataset_version_id,
                        line_number=line_number,
                        status=row_status,
                        original_json=json.dumps(original, ensure_ascii=False, sort_keys=True),
                        normalized_json=json.dumps(
                            normalized, ensure_ascii=False, sort_keys=True
                        ),
                        errors_json=json.dumps(errors, ensure_ascii=False),
                        row_hash=row_hash,
                    )
                )
                if len(batch) >= payload.batch_size:
                    add_rows(session, batch)
                    batch = []

        if batch:
            add_rows(session, batch)
        execution.status = "COMPLETED"
        execution.completed_at = datetime.now(timezone.utc)
        save_execution(session, execution)
        return _summary(execution)
    except Exception as error:
        session.rollback()
        execution.status = "FAILED"
        execution.error_message = str(error)[:5000]
        execution.completed_at = datetime.now(timezone.utc)
        save_execution(session, execution)
        if isinstance(error, DatasetImportStagingError):
            raise
        raise DatasetImportStagingValidationError(str(error)) from error


def get_dataset_version_staging_summary(
    session: Session, *, dataset_version_id: str
) -> DatasetImportStagingSummaryResponse:
    version = get_dataset_version(session, dataset_version_id)
    if version is None:
        raise DatasetImportStagingNotFoundError("Versão de dataset não encontrada.")
    execution = get_latest_execution(session, dataset_version_id)
    if execution is None:
        raise DatasetImportStagingNotFoundError(
            "Nenhuma execução de staging foi encontrada para esta versão."
        )
    return _summary(execution)


def list_dataset_version_rejected_rows(
    session: Session,
    *,
    dataset_version_id: str,
    status: DatasetImportRowStatus | None,
    limit: int,
    offset: int,
) -> DatasetImportRejectedRowsListResponse:
    execution = get_latest_execution(session, dataset_version_id)
    if execution is None:
        raise DatasetImportStagingNotFoundError(
            "Nenhuma execução de staging foi encontrada para esta versão."
        )
    if status == DatasetImportRowStatus.VALID:
        raise DatasetImportStagingValidationError(
            "A listagem de rejeitados aceita apenas INVALID ou DUPLICATE."
        )
    total, rows = list_rejected_rows(
        session,
        execution_id=execution.execution_id,
        status=status.value if status else None,
        limit=limit,
        offset=offset,
    )
    return DatasetImportRejectedRowsListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[_row_response(row) for row in rows],
    )
