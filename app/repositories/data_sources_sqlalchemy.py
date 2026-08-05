from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.data_source_model import DataSourceModel


def add_data_source(session: Session, model: DataSourceModel) -> DataSourceModel:
    session.add(model)
    session.commit()
    session.refresh(model)
    return model


def save_data_source(session: Session, model: DataSourceModel) -> DataSourceModel:
    session.add(model)
    session.commit()
    session.refresh(model)
    return model


def get_data_source(session: Session, data_source_id: str) -> DataSourceModel | None:
    return session.get(DataSourceModel, data_source_id)


def get_data_source_by_name_key(
    session: Session, name_key: str
) -> DataSourceModel | None:
    statement = select(DataSourceModel).where(DataSourceModel.name_key == name_key)
    return session.scalar(statement)


def list_data_sources(
    session: Session,
    *,
    status: str | None = None,
    source_type: str | None = None,
    responsible: str | None = None,
    name: str | None = None,
    limit: int,
    offset: int,
) -> tuple[int, Sequence[DataSourceModel]]:
    filters = []
    if status is not None:
        filters.append(DataSourceModel.status == status)
    if source_type is not None:
        filters.append(func.lower(DataSourceModel.source_type) == source_type.lower())
    if responsible is not None:
        filters.append(
            func.lower(DataSourceModel.responsible).contains(responsible.lower())
        )
    if name is not None:
        filters.append(func.lower(DataSourceModel.name).contains(name.lower()))

    total = int(
        session.scalar(
            select(func.count(DataSourceModel.data_source_id)).where(*filters)
        )
        or 0
    )
    statement = (
        select(DataSourceModel)
        .where(*filters)
        .order_by(DataSourceModel.created_at.desc(), DataSourceModel.name.asc())
        .limit(limit)
        .offset(offset)
    )
    return total, session.scalars(statement).all()
