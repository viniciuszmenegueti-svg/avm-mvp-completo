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
        .order_by(
            CityModel.name.asc(),
        )
    )

    database_cities = session.scalars(
        statement
    ).all()

    return [
        CityResponse.model_validate(city)
        for city in database_cities
    ]
