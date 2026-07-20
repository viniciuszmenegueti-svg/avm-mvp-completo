from sqlalchemy.orm import Session

from app.domain.exceptions import (
    CityDataMismatchError,
    UnsupportedCityError,
)
from app.repositories.cities_sqlalchemy import (
    get_active_city_by_ibge_code,
)
from app.schemas.order import OrderCreate


def validate_order_city(
    session: Session,
    order: OrderCreate,
) -> None:
    property_data = order.property

    city = get_active_city_by_ibge_code(
        session=session,
        city_ibge_code=property_data.city_ibge_code,
    )

    if city is None:
        raise UnsupportedCityError(
            city_ibge_code=property_data.city_ibge_code,
        )

    informed_city = property_data.city.strip().casefold()
    registered_city = city.name.strip().casefold()

    informed_state = property_data.state.strip().upper()
    registered_state = city.state.strip().upper()

    if informed_city != registered_city or informed_state != registered_state:
        raise CityDataMismatchError(
            city_ibge_code=property_data.city_ibge_code,
            expected_city=city.name,
            expected_state=city.state,
        )
