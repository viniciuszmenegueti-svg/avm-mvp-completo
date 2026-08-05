from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.domain.dataset_import_staging_model import (
    DatasetImportExecutionModel,
    DatasetImportRowModel,
)


def add_execution(
    session: Session, model: DatasetImportExecutionModel
) -> DatasetImportExecutionModel:
    session.add(model)
    session.commit()
    session.refresh(model)
    return model


def save_execution(
    session: Session, model: DatasetImportExecutionModel
) -> DatasetImportExecutionModel:
    session.add(model)
    session.commit()
    session.refresh(model)
    return model


def get_execution(
    session: Session, execution_id: str
) -> DatasetImportExecutionModel | None:
    return session.get(DatasetImportExecutionModel, execution_id)


def get_latest_execution(
    session: Session, dataset_version_id: str
) -> DatasetImportExecutionModel | None:
    statement = (
        select(DatasetImportExecutionModel)
        .where(DatasetImportExecutionModel.dataset_version_id == dataset_version_id)
        .order_by(
            DatasetImportExecutionModel.created_at.desc(),
            DatasetImportExecutionModel.execution_id.desc(),
        )
        .limit(1)
    )
    return session.scalar(statement)


def get_running_execution(
    session: Session, dataset_version_id: str
) -> DatasetImportExecutionModel | None:
    statement = select(DatasetImportExecutionModel).where(
        DatasetImportExecutionModel.dataset_version_id == dataset_version_id,
        DatasetImportExecutionModel.status == "RUNNING",
    )
    return session.scalar(statement)


def add_rows(session: Session, rows: Sequence[DatasetImportRowModel]) -> None:
    session.add_all(rows)
    session.flush()


def delete_staging_for_version(session: Session, dataset_version_id: str) -> None:
    execution_ids = select(DatasetImportExecutionModel.execution_id).where(
        DatasetImportExecutionModel.dataset_version_id == dataset_version_id
    )
    session.execute(
        delete(DatasetImportRowModel).where(
            DatasetImportRowModel.execution_id.in_(execution_ids)
        )
    )
    session.execute(
        delete(DatasetImportExecutionModel).where(
            DatasetImportExecutionModel.dataset_version_id == dataset_version_id
        )
    )
    session.commit()


def list_rejected_rows(
    session: Session,
    *,
    execution_id: str,
    status: str | None,
    limit: int,
    offset: int,
) -> tuple[int, Sequence[DatasetImportRowModel]]:
    filters = [
        DatasetImportRowModel.execution_id == execution_id,
        DatasetImportRowModel.status.in_(("INVALID", "DUPLICATE")),
    ]
    if status is not None:
        filters.append(DatasetImportRowModel.status == status)

    total = int(
        session.scalar(
            select(func.count(DatasetImportRowModel.row_id)).where(*filters)
        )
        or 0
    )
    statement = (
        select(DatasetImportRowModel)
        .where(*filters)
        .order_by(DatasetImportRowModel.line_number.asc())
        .limit(limit)
        .offset(offset)
    )
    return total, session.scalars(statement).all()
