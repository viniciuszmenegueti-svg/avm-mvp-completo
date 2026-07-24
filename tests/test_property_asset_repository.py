from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from app.domain.city_model import CityModel
from app.infrastructure.database import SessionLocal
from app.repositories.property_assets_sqlalchemy import (
    create_property_asset,
    get_property_asset_by_id,
)
from app.schemas.property_asset import PropertyAssetCreate


def create_test_city() -> None:
    with SessionLocal() as session:
        existing_city = (
            session.query(CityModel)
            .filter(
                CityModel.city_ibge_code == "3205309",
            )
            .first()
        )

        if existing_city is not None:
            return

        city = CityModel(
            city_ibge_code="3205309",
            name="Venda Nova do Imigrante",
            state="ES",
        )

        session.add(city)

        try:
            session.commit()
        except IntegrityError:
            session.rollback()


def valid_property_asset() -> PropertyAssetCreate:
    return PropertyAssetCreate(
        property_type="APARTMENT",
        city_ibge_code="3205309",
        postal_code="29375000",
        neighborhood="Centro",
        street="Rua Teste",
        number="100",
        private_area_m2=72.50,
        built_area_m2=85.00,
        land_area_m2=None,
        bedrooms=3,
        bathrooms=2,
        parking_spaces=1,
    )


def test_creates_property_asset() -> None:
    create_test_city()

    property_asset_id = str(uuid4())

    with SessionLocal() as session:
        property_asset = create_property_asset(
            session=session,
            property_asset_id=property_asset_id,
            property_asset=valid_property_asset(),
        )

    assert property_asset.property_asset_id == property_asset_id
    assert property_asset.property_type == "APARTMENT"
    assert property_asset.city_ibge_code == "3205309"


def test_gets_property_asset_by_id() -> None:
    create_test_city()

    property_asset_id = str(uuid4())

    with SessionLocal() as session:
        create_property_asset(
            session=session,
            property_asset_id=property_asset_id,
            property_asset=valid_property_asset(),
        )

        stored_property_asset = get_property_asset_by_id(
            session=session,
            property_asset_id=property_asset_id,
        )

    assert stored_property_asset is not None
    assert stored_property_asset.property_asset_id == property_asset_id
    assert stored_property_asset.postal_code == "29375000"


def test_returns_none_for_unknown_property_asset() -> None:
    with SessionLocal() as session:
        property_asset = get_property_asset_by_id(
            session=session,
            property_asset_id=str(uuid4()),
        )

    assert property_asset is None
