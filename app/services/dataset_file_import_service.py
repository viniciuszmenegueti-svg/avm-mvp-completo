import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.domain.dataset_version_model import DatasetVersionModel
from app.infrastructure.database import PROJECT_ROOT
from app.repositories.dataset_versions_sqlalchemy import (
    get_dataset_version,
    save_dataset_version,
)
from app.schemas.dataset_file_import import (
    DatasetFileImportResultResponse,
    DatasetFileUploadResponse,
)
from app.schemas.dataset_version import DatasetVersionStatus


DEFAULT_MAX_UPLOAD_BYTES = 50 * 1024 * 1024
ALLOWED_MIME_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "application/octet-stream",
}


class DatasetFileImportError(Exception):
    pass


class DatasetFileNotFoundError(DatasetFileImportError):
    pass


class DatasetFileStatusConflictError(DatasetFileImportError):
    pass


class DatasetFileValidationError(DatasetFileImportError):
    pass


class DatasetFileChecksumMismatchError(DatasetFileImportError):
    pass


class DatasetFileSizeMismatchError(DatasetFileImportError):
    pass


class DatasetFileAlreadyUploadedError(DatasetFileImportError):
    pass


class DatasetFileProcessingError(DatasetFileImportError):
    pass


def _storage_root() -> Path:
    configured = os.getenv("DATASET_UPLOAD_DIR")
    root = Path(configured) if configured else PROJECT_ROOT / "data" / "dataset_uploads"
    return root.resolve()


def _max_upload_bytes() -> int:
    raw = os.getenv("DATASET_MAX_UPLOAD_BYTES", str(DEFAULT_MAX_UPLOAD_BYTES))
    try:
        value = int(raw)
    except ValueError as error:
        raise DatasetFileValidationError(
            "DATASET_MAX_UPLOAD_BYTES precisa ser um número inteiro."
        ) from error
    if value <= 0:
        raise DatasetFileValidationError(
            "DATASET_MAX_UPLOAD_BYTES precisa ser maior que zero."
        )
    return value


def _validated_file_name(file_name: str | None) -> str:
    if not file_name:
        raise DatasetFileValidationError("O nome do arquivo é obrigatório.")
    normalized = Path(file_name).name.strip()
    if not normalized or normalized != file_name.strip():
        raise DatasetFileValidationError("O nome do arquivo contém um caminho inválido.")
    if Path(normalized).suffix.lower() != ".csv":
        raise DatasetFileValidationError("Somente arquivos CSV são aceitos.")
    return normalized


def _validated_mime_type(content_type: str | None) -> str:
    normalized = (content_type or "application/octet-stream").split(";", 1)[0].strip().lower()
    if normalized not in ALLOWED_MIME_TYPES:
        raise DatasetFileValidationError(
            f"Tipo MIME não permitido para CSV: {normalized}."
        )
    return normalized


def _destination_for(model: DatasetVersionModel, root: Path) -> tuple[Path, str]:
    try:
        UUID(model.dataset_id)
        UUID(model.dataset_version_id)
    except ValueError as error:
        raise DatasetFileValidationError("Identificador de dataset inválido.") from error

    relative = Path(model.dataset_id) / f"v{model.version_number}" / "source.csv"
    destination = (root / relative).resolve()
    try:
        destination.relative_to(root)
    except ValueError as error:
        raise DatasetFileValidationError("Caminho de armazenamento inválido.") from error
    return destination, relative.as_posix()


async def upload_dataset_version_file(
    session: Session,
    *,
    dataset_version_id: str,
    upload: UploadFile,
    actor: str,
) -> DatasetFileUploadResponse:
    model = get_dataset_version(session, dataset_version_id)
    if model is None:
        raise DatasetFileNotFoundError("Versão de dataset não encontrada.")
    if model.status != DatasetVersionStatus.REGISTERED.value:
        raise DatasetFileStatusConflictError(
            "O upload só é permitido para versões com status REGISTERED."
        )

    file_name = _validated_file_name(upload.filename)
    mime_type = _validated_mime_type(upload.content_type)
    root = _storage_root()
    destination, relative_path = _destination_for(model, root)
    if destination.exists():
        raise DatasetFileAlreadyUploadedError(
            "Já existe um arquivo armazenado para esta versão do dataset."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".uploading")
    digest = hashlib.sha256()
    size = 0
    limit = _max_upload_bytes()

    try:
        with temporary.open("xb") as output:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > limit:
                    raise DatasetFileValidationError(
                        f"O arquivo excede o limite de {limit} bytes."
                    )
                digest.update(chunk)
                output.write(chunk)

        if size == 0:
            raise DatasetFileValidationError("O arquivo enviado está vazio.")

        checksum = digest.hexdigest()
        if checksum != model.checksum_sha256.lower():
            raise DatasetFileChecksumMismatchError(
                "O checksum do arquivo enviado não corresponde ao registro da versão."
            )
        if size != model.file_size_bytes:
            raise DatasetFileSizeMismatchError(
                "O tamanho do arquivo enviado não corresponde ao registro da versão."
            )

        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()

    model.file_name = file_name
    model.storage_path = relative_path
    model.mime_type = mime_type
    model.updated_by = actor
    save_dataset_version(session, model)

    return DatasetFileUploadResponse(
        dataset_version_id=model.dataset_version_id,
        file_name=model.file_name,
        storage_path=model.storage_path,
        checksum_sha256=model.checksum_sha256,
        file_size_bytes=model.file_size_bytes,
        mime_type=mime_type,
    )


def _claim_processing(
    session: Session,
    *,
    dataset_version_id: str,
    actor: str,
) -> DatasetVersionModel:
    started_at = datetime.now(timezone.utc)
    result = session.execute(
        update(DatasetVersionModel)
        .where(
            DatasetVersionModel.dataset_version_id == dataset_version_id,
            DatasetVersionModel.status == DatasetVersionStatus.REGISTERED.value,
        )
        .values(
            status=DatasetVersionStatus.PROCESSING.value,
            processing_started_at=started_at,
            completed_at=None,
            error_message=None,
            updated_by=actor,
        )
    )
    if result.rowcount != 1:
        session.rollback()
        model = get_dataset_version(session, dataset_version_id)
        if model is None:
            raise DatasetFileNotFoundError("Versão de dataset não encontrada.")
        raise DatasetFileStatusConflictError(
            "A versão já foi processada ou está sendo processada."
        )
    session.commit()
    model = get_dataset_version(session, dataset_version_id)
    assert model is not None
    return model


def _open_csv(path: Path) -> tuple[BinaryIO, str]:
    stream = path.open("rb")
    prefix = stream.read(3)
    stream.seek(0)
    if prefix.startswith(b"\xef\xbb\xbf"):
        return stream, "utf-8-sig"
    return stream, "utf-8"


def _inspect_csv(path: Path) -> tuple[list[str], int, str, str]:
    binary_stream, encoding = _open_csv(path)
    try:
        text_stream = __import__("io").TextIOWrapper(
            binary_stream,
            encoding=encoding,
            errors="strict",
            newline="",
        )
        sample = text_stream.read(8192)
        if not sample.strip():
            raise DatasetFileValidationError("O arquivo CSV está vazio.")
        text_stream.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        reader = csv.reader(text_stream, dialect)
        try:
            raw_headers = next(reader)
        except StopIteration as error:
            raise DatasetFileValidationError("O arquivo CSV não possui cabeçalho.") from error

        headers = [header.strip() for header in raw_headers]
        if not headers or any(not header for header in headers):
            raise DatasetFileValidationError(
                "O cabeçalho contém colunas vazias."
            )
        normalized = [header.casefold() for header in headers]
        if len(set(normalized)) != len(normalized):
            raise DatasetFileValidationError(
                "O cabeçalho contém nomes de colunas duplicados."
            )

        record_count = 0
        for line_number, row in enumerate(reader, start=2):
            if not row or all(not value.strip() for value in row):
                continue
            if len(row) != len(headers):
                raise DatasetFileValidationError(
                    f"A linha {line_number} possui {len(row)} campos; esperados {len(headers)}."
                )
            record_count += 1

        return headers, record_count, dialect.delimiter, encoding
    except UnicodeDecodeError as error:
        raise DatasetFileValidationError(
            "O CSV precisa estar codificado em UTF-8."
        ) from error
    except csv.Error as error:
        raise DatasetFileValidationError(f"CSV inválido: {error}.") from error
    finally:
        if not binary_stream.closed:
            binary_stream.close()


def _metadata(model: DatasetVersionModel) -> dict[str, Any]:
    try:
        value = json.loads(model.metadata_json)
    except (TypeError, json.JSONDecodeError):
        value = {}
    return value if isinstance(value, dict) else {}


def process_dataset_version_file(
    session: Session,
    *,
    dataset_version_id: str,
    actor: str,
) -> DatasetFileImportResultResponse:
    model = _claim_processing(
        session,
        dataset_version_id=dataset_version_id,
        actor=actor,
    )
    root = _storage_root()
    path = (root / model.storage_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        validation_error = DatasetFileValidationError(
            "O caminho do arquivo está fora do diretório permitido."
        )
        _mark_failed(session, model, validation_error, actor)
        raise validation_error from error

    try:
        if not path.is_file():
            raise DatasetFileValidationError(
                "O arquivo da versão não foi encontrado no armazenamento."
            )
        headers, record_count, delimiter, encoding = _inspect_csv(path)
        metadata = _metadata(model)
        metadata["file_import"] = {
            "columns": headers,
            "delimiter": delimiter,
            "encoding": encoding,
        }
        model.status = DatasetVersionStatus.COMPLETED.value
        model.record_count = record_count
        model.metadata_json = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
        model.completed_at = datetime.now(timezone.utc)
        model.error_message = None
        model.updated_by = actor
        save_dataset_version(session, model)
        return _result(model)
    except DatasetFileValidationError as error:
        _mark_failed(session, model, error, actor)
        raise DatasetFileProcessingError(str(error)) from error


def _mark_failed(
    session: Session,
    model: DatasetVersionModel,
    error: Exception,
    actor: str,
) -> None:
    model.status = DatasetVersionStatus.FAILED.value
    model.error_message = str(error)[:5000]
    model.completed_at = datetime.now(timezone.utc)
    model.updated_by = actor
    save_dataset_version(session, model)


def _result(model: DatasetVersionModel) -> DatasetFileImportResultResponse:
    metadata = _metadata(model)
    import_metadata = metadata.get("file_import", {})
    if not isinstance(import_metadata, dict):
        import_metadata = {}
    columns = import_metadata.get("columns", [])
    return DatasetFileImportResultResponse(
        dataset_version_id=model.dataset_version_id,
        status=DatasetVersionStatus(model.status),
        record_count=model.record_count,
        columns=columns if isinstance(columns, list) else [],
        delimiter=import_metadata.get("delimiter"),
        encoding=import_metadata.get("encoding"),
        error_message=model.error_message,
        processing_started_at=model.processing_started_at,
        completed_at=model.completed_at,
        metadata=metadata,
    )


def get_dataset_version_import_result(
    session: Session,
    *,
    dataset_version_id: str,
) -> DatasetFileImportResultResponse:
    model = get_dataset_version(session, dataset_version_id)
    if model is None:
        raise DatasetFileNotFoundError("Versão de dataset não encontrada.")
    return _result(model)
