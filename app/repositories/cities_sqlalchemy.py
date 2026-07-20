from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.city_model import CityModel
from app.schemas.city import CityResponse


def list_active_cities(
    session: Session,
) -> list[CityResponse]:
    statement = (
        select(CityModel)
        .where(CityModel.active.is_(True))
        .order_by(CityModel.name.asc())
    )

    database_cities = session.scalars(statement).all()

    return [CityResponse.model_validate(city) for city in database_cities]


def get_active_city_by_ibge_code(
    session: Session,
    city_ibge_code: str,
) -> CityResponse | None:
    statement = select(CityModel).where(
        CityModel.city_ibge_code == city_ibge_code,
        CityModel.active.is_(True),
    )

    database_city = session.scalar(statement)

    if database_city is None:
        return None

    return CityResponse.model_validate(database_city)
