from sqlalchemy.orm import Session

from app.domain.property_asset_model import (
    PropertyAssetModel,
)
from app.schemas.property_asset import (
    PropertyAssetCreate,
)


def create_property_asset(
    session: Session,
    property_asset_id: str,
    property_asset: PropertyAssetCreate,
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
    session: Session,
    property_asset_id: str,
) -> PropertyAssetModel | None:
    return (
        session.query(PropertyAssetModel)
        .filter(
            PropertyAssetModel.property_asset_id == property_asset_id,
        )
        .first()
    )
