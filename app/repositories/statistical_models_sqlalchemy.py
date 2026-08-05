from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.domain.statistical_dataset_model import StatisticalDatasetModel
from app.domain.statistical_model_version_model import StatisticalModelVersionModel


def create_dataset_and_model(
    session: Session,
    *,
    dataset: StatisticalDatasetModel,
    model: StatisticalModelVersionModel,
) -> None:
    session.add(dataset)
    session.add(model)
    session.commit()
    session.refresh(dataset)
    session.refresh(model)


def get_statistical_model(
    session: Session, model_id: str
) -> StatisticalModelVersionModel | None:
    return session.get(StatisticalModelVersionModel, model_id)


def get_statistical_model_for_update(
    session: Session, model_id: str
) -> StatisticalModelVersionModel | None:
    statement = (
        select(StatisticalModelVersionModel)
        .where(StatisticalModelVersionModel.model_id == model_id)
        .with_for_update()
    )
    return session.scalar(statement)


def get_statistical_dataset(
    session: Session, dataset_id: str
) -> StatisticalDatasetModel | None:
    return session.get(StatisticalDatasetModel, dataset_id)


def list_statistical_models(
    session: Session,
) -> list[StatisticalModelVersionModel]:
    statement = select(StatisticalModelVersionModel).order_by(
        StatisticalModelVersionModel.trained_at.desc(),
        StatisticalModelVersionModel.model_id.desc(),
    )
    return list(session.scalars(statement).all())


def get_applicable_statistical_model(
    session: Session,
    *,
    city_ibge_code: str,
    property_type: str,
    required_status: str,
    reference_date: date,
) -> StatisticalModelVersionModel | None:
    statement = (
        select(StatisticalModelVersionModel)
        .where(
            StatisticalModelVersionModel.city_ibge_code == city_ibge_code,
            StatisticalModelVersionModel.property_type == property_type,
            StatisticalModelVersionModel.status == required_status,
            StatisticalModelVersionModel.valid_from <= reference_date,
            or_(
                StatisticalModelVersionModel.valid_until.is_(None),
                StatisticalModelVersionModel.valid_until >= reference_date,
            ),
        )
        .order_by(
            StatisticalModelVersionModel.valid_from.desc(),
            StatisticalModelVersionModel.approved_at.desc(),
        )
        .limit(1)
    )
    return session.scalar(statement)


def disable_other_homologation_models(
    session: Session,
    *,
    selected_model: StatisticalModelVersionModel,
) -> None:
    statement = (
        select(StatisticalModelVersionModel)
        .where(
            StatisticalModelVersionModel.city_ibge_code
            == selected_model.city_ibge_code,
            StatisticalModelVersionModel.property_type == selected_model.property_type,
            StatisticalModelVersionModel.status == "HOMOLOGATION_APPROVED",
            StatisticalModelVersionModel.model_id != selected_model.model_id,
        )
        .with_for_update()
    )
    for model in session.scalars(statement):
        model.status = "DISABLED"
