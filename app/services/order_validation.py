from sqlalchemy.orm import Session

from app.domain.exceptions import UnsupportedCityError
from app.repositories.cities_sqlalchemy import (
    get_active_city_by_ibge_code,
)
from app.schemas.order import OrderCreate


def validate_order_city(
    session: Session,
    order: OrderCreate,
) -> None:
    city = get_active_city_by_ibge_code(
        session=session,
        city_ibge_code=order.property.city_ibge_code,
    )

    if city is None:
        raise UnsupportedCityError(
            city_ibge_code=(
                order.property.city_ibge_code
            ),
        )
