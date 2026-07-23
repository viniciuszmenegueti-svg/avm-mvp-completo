from fastapi import APIRouter

from app.infrastructure.dependencies import (
    DatabaseSession,
)
from app.repositories.cities_sqlalchemy import (
    list_active_cities,
)
from app.repositories.city_valuation_prices_sqlalchemy import (
    list_city_valuation_prices,
)
from app.schemas.city import CityResponse
from app.schemas.city_valuation_price import (
    CityValuationPriceResponse,
)


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


@router.get(
    "/{city_ibge_code}/valuation-prices",
    response_model=list[CityValuationPriceResponse],
    summary="Lista os preços-base de avaliação da cidade",
)
def get_city_valuation_prices(
    city_ibge_code: str,
    session: DatabaseSession,
) -> list[CityValuationPriceResponse]:
    return list_city_valuation_prices(
        session=session,
        city_ibge_code=city_ibge_code,
    )
