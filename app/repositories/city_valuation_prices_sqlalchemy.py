from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.city_valuation_price_model import (
    CityValuationPriceModel,
)
from app.schemas.city_valuation_price import (
    CityValuationPriceResponse,
)
from app.schemas.property import PropertyType


def get_city_valuation_price(
    session: Session,
    city_ibge_code: str,
    property_type: PropertyType,
) -> CityValuationPriceResponse | None:
    statement = select(CityValuationPriceModel).where(
        CityValuationPriceModel.city_ibge_code == city_ibge_code,
        CityValuationPriceModel.property_type == property_type.value,
    )

    database_price = session.scalar(statement)

    if database_price is None:
        return None

    return CityValuationPriceResponse.model_validate(database_price)


def list_city_valuation_prices(
    session: Session,
    city_ibge_code: str,
) -> list[CityValuationPriceResponse]:
    statement = (
        select(CityValuationPriceModel)
        .where(CityValuationPriceModel.city_ibge_code == city_ibge_code)
        .order_by(CityValuationPriceModel.property_type.asc())
    )

    database_prices = session.scalars(statement).all()

    return [
        CityValuationPriceResponse.model_validate(database_price)
        for database_price in database_prices
    ]
