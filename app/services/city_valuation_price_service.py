from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.city_valuation_price_history_sqlalchemy import (
    create_city_valuation_price_history,
)
from app.repositories.city_valuation_prices_sqlalchemy import (
    get_city_valuation_price,
    update_city_valuation_price,
)
from app.schemas.city_valuation_price import (
    CityValuationPriceResponse,
)
from app.schemas.property import PropertyType


def update_city_valuation_price_with_history(
    session: Session,
    city_ibge_code: str,
    property_type: PropertyType,
    price_per_m2: Decimal,
) -> CityValuationPriceResponse | None:
    current_price = get_city_valuation_price(
        session=session,
        city_ibge_code=city_ibge_code,
        property_type=property_type,
    )

    if current_price is None:
        return None

    if current_price.price_per_m2 == price_per_m2:
        return current_price

    try:
        updated_price = update_city_valuation_price(
            session=session,
            city_ibge_code=city_ibge_code,
            property_type=property_type,
            price_per_m2=price_per_m2,
            commit=False,
        )

        if updated_price is None:
            session.rollback()
            return None

        create_city_valuation_price_history(
            session=session,
            city_valuation_price_id=current_price.id,
            city_ibge_code=city_ibge_code,
            property_type=property_type,
            previous_price_per_m2=(current_price.price_per_m2),
            new_price_per_m2=price_per_m2,
            commit=False,
        )

        session.commit()

        return updated_price

    except Exception:
        session.rollback()
        raise
