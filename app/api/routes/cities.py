from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.infrastructure.dependencies import (
    get_database_session,
)
from app.repositories.cities_sqlalchemy import (
    list_active_cities,
)
from app.schemas.city import CityResponse


router = APIRouter(
    prefix="/cities",
    tags=["Cidades"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


@router.get(
    "",
    response_model=list[CityResponse],
    summary="Lista as cidades ativas para AVM",
)
def get_cities(
    session: DatabaseSession,
) -> list[CityResponse]:
    return list_active_cities(session)
