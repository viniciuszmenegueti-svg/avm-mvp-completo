from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.property_asset_model import PropertyAssetModel
from app.schemas.property_asset import PropertyAssetCreate


def create_property_asset(
    session: Session, property_asset_id: str, property_asset: PropertyAssetCreate
) -> PropertyAssetModel:
    database_property_asset = PropertyAssetModel(
        property_asset_id=property_asset_id,
        **property_asset.model_dump(),
    )
    session.add(database_property_asset)
    session.commit()
    session.refresh(database_property_asset)
    return database_property_asset


def get_property_asset_by_id(
    session: Session, property_asset_id: str
) -> PropertyAssetModel | None:
    return session.get(PropertyAssetModel, property_asset_id)


def find_matching_property_asset(
    session: Session, property_asset: PropertyAssetCreate
) -> PropertyAssetModel | None:
    statement = select(PropertyAssetModel).where(
        PropertyAssetModel.property_type == property_asset.property_type.value,
        PropertyAssetModel.city_ibge_code == property_asset.city_ibge_code,
        PropertyAssetModel.postal_code == property_asset.postal_code,
        func.lower(PropertyAssetModel.street) == property_asset.street.lower(),
        func.lower(PropertyAssetModel.number) == property_asset.number.lower(),
        func.coalesce(func.lower(PropertyAssetModel.complement), "")
        == (property_asset.complement or "").lower(),
    )
    return session.scalar(statement)


def list_property_assets(
    session: Session,
    limit: int,
    offset: int,
    city_ibge_code: str | None = None,
) -> tuple[list[PropertyAssetModel], int]:
    filters = []
    if city_ibge_code is not None:
        filters.append(PropertyAssetModel.city_ibge_code == city_ibge_code)
    total = (
        session.scalar(
            select(func.count(PropertyAssetModel.property_asset_id)).where(*filters)
        )
        or 0
    )
    statement = (
        select(PropertyAssetModel)
        .where(*filters)
        .order_by(PropertyAssetModel.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(statement).all()), total


def update_property_asset(
    session: Session,
    property_asset_id: str,
    property_asset: PropertyAssetCreate,
) -> PropertyAssetModel | None:
    asset = session.get(PropertyAssetModel, property_asset_id)
    if asset is None:
        return None

    # Recebe um estado completo já validado. O flush torna valores gerados pelo
    # banco (como updated_at) disponíveis para validar a resposta, mas deixa o
    # commit sob responsabilidade da rota: uma falha posterior ainda faz rollback.
    for field, value in property_asset.model_dump().items():
        setattr(asset, field, value)
    session.flush()
    session.refresh(asset)
    return asset
