from fastapi import APIRouter

from app.infrastructure.dependencies import (
    DatabaseSession,
)
from app.repositories.cities_sqlalchemy import (
    list_active_cities,
)
from app.schemas.city import CityResponse


router = APIRouter(
    prefix="/cities",
    tags=["Cidades"],
)


@router.get(
    "",
    response_model=list[CityResponse],
    summary="Lista as cidades ativas para AVM",
)
def get_cities(
    session: DatabaseSession,
) -> list[CityResponse]:
    return list_active_cities(session)
