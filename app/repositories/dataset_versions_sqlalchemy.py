from collections.abc import Sequence
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.dataset_version_model import DatasetVersionModel


def add_dataset_version(
    session: Session,
    model: DatasetVersionModel,
) -> DatasetVersionModel:
    session.add(model)
    session.commit()
    session.refresh(model)
    return model


def save_dataset_version(
    session: Session,
    model: DatasetVersionModel,
) -> DatasetVersionModel:
    session.add(model)
    session.commit()
    session.refresh(model)
    return model


def get_dataset_version(
    session: Session,
    dataset_version_id: str,
) -> DatasetVersionModel | None:
    return session.get(DatasetVersionModel, dataset_version_id)


def get_dataset_version_by_checksum(
    session: Session,
    *,
    dataset_id: str,
    checksum_sha256: str,
) -> DatasetVersionModel | None:
    statement = select(DatasetVersionModel).where(
        DatasetVersionModel.dataset_id == dataset_id,
        DatasetVersionModel.checksum_sha256 == checksum_sha256,
    )
    return session.scalar(statement)


def next_dataset_version_number(session: Session, dataset_id: str) -> int:
    current = session.scalar(
        select(func.max(DatasetVersionModel.version_number)).where(
            DatasetVersionModel.dataset_id == dataset_id
        )
    )
    return int(current or 0) + 1


def list_dataset_versions(
    session: Session,
    *,
    dataset_id: str | None = None,
    status: str | None = None,
    created_by: str | None = None,
    checksum_sha256: str | None = None,
    reference_from: date | None = None,
    reference_until: date | None = None,
    limit: int,
    offset: int,
) -> tuple[int, Sequence[DatasetVersionModel]]:
    filters = []
    if dataset_id is not None:
        filters.append(DatasetVersionModel.dataset_id == dataset_id)
    if status is not None:
        filters.append(DatasetVersionModel.status == status)
    if created_by is not None:
        filters.append(DatasetVersionModel.created_by == created_by)
    if checksum_sha256 is not None:
        filters.append(DatasetVersionModel.checksum_sha256 == checksum_sha256)
    if reference_from is not None:
        filters.append(
            (DatasetVersionModel.reference_end.is_(None))
            | (DatasetVersionModel.reference_end >= reference_from)
        )
    if reference_until is not None:
        filters.append(
            (DatasetVersionModel.reference_start.is_(None))
            | (DatasetVersionModel.reference_start <= reference_until)
        )

    total = int(
        session.scalar(
            select(func.count(DatasetVersionModel.dataset_version_id)).where(*filters)
        )
        or 0
    )
    statement = (
        select(DatasetVersionModel)
        .where(*filters)
        .order_by(
            DatasetVersionModel.created_at.desc(),
            DatasetVersionModel.version_number.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    return total, session.scalars(statement).all()
