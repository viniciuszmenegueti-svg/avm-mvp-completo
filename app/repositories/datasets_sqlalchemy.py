from collections.abc import Sequence
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.dataset_model import DatasetModel


def add_dataset(session: Session, model: DatasetModel) -> DatasetModel:
    session.add(model)
    session.commit()
    session.refresh(model)
    return model


def save_dataset(session: Session, model: DatasetModel) -> DatasetModel:
    session.add(model)
    session.commit()
    session.refresh(model)
    return model


def get_dataset(session: Session, dataset_id: str) -> DatasetModel | None:
    return session.get(DatasetModel, dataset_id)


def get_dataset_by_source_and_name_key(
    session: Session,
    *,
    data_source_id: str,
    name_key: str,
) -> DatasetModel | None:
    statement = select(DatasetModel).where(
        DatasetModel.data_source_id == data_source_id,
        DatasetModel.name_key == name_key,
    )
    return session.scalar(statement)


def list_datasets(
    session: Session,
    *,
    data_source_id: str | None = None,
    status: str | None = None,
    name: str | None = None,
    reference_from: date | None = None,
    reference_until: date | None = None,
    limit: int,
    offset: int,
) -> tuple[int, Sequence[DatasetModel]]:
    filters = []
    if data_source_id is not None:
        filters.append(DatasetModel.data_source_id == data_source_id)
    if status is not None:
        filters.append(DatasetModel.status == status)
    if name is not None:
        filters.append(func.lower(DatasetModel.name).contains(name.lower()))
    if reference_from is not None:
        filters.append(
            (DatasetModel.reference_end.is_(None))
            | (DatasetModel.reference_end >= reference_from)
        )
    if reference_until is not None:
        filters.append(
            (DatasetModel.reference_start.is_(None))
            | (DatasetModel.reference_start <= reference_until)
        )

    total = int(
        session.scalar(select(func.count(DatasetModel.dataset_id)).where(*filters))
        or 0
    )
    statement = (
        select(DatasetModel)
        .where(*filters)
        .order_by(DatasetModel.created_at.desc(), DatasetModel.name.asc())
        .limit(limit)
        .offset(offset)
    )
    return total, session.scalars(statement).all()
