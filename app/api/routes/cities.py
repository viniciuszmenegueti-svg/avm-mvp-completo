from fastapi import APIRouter, HTTPException, status

from app.infrastructure.dependencies import (
    DatabaseSession,
)
from app.repositories.cities_sqlalchemy import (
    list_active_cities,
)
from app.repositories.city_valuation_price_history_sqlalchemy import (
    list_city_valuation_price_history,
)
from app.repositories.city_valuation_prices_sqlalchemy import (
    list_city_valuation_prices,
)
from app.schemas.city import CityResponse
from app.schemas.city_valuation_price import (
    CityValuationPriceResponse,
    CityValuationPriceUpdate,
)
from app.schemas.city_valuation_price_history import (
    CityValuationPriceHistoryResponse,
)
from app.schemas.property import PropertyType
from app.services.city_valuation_price_service import (
    update_city_valuation_price_with_history,
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


@router.get(
    "/{city_ibge_code}/valuation-prices/{property_type}/history",
    response_model=list[CityValuationPriceHistoryResponse],
    summary="Lista o histórico do preço-base de avaliação",
)
def get_city_valuation_price_history(
    city_ibge_code: str,
    property_type: PropertyType,
    session: DatabaseSession,
) -> list[CityValuationPriceHistoryResponse]:
    return list_city_valuation_price_history(
        session=session,
        city_ibge_code=city_ibge_code,
        property_type=property_type,
    )


@router.patch(
    "/{city_ibge_code}/valuation-prices/{property_type}",
    response_model=CityValuationPriceResponse,
    summary="Atualiza o preço-base de avaliação",
)
def patch_city_valuation_price(
    city_ibge_code: str,
    property_type: PropertyType,
    payload: CityValuationPriceUpdate,
    session: DatabaseSession,
) -> CityValuationPriceResponse:
    updated_price = update_city_valuation_price_with_history(
        session=session,
        city_ibge_code=city_ibge_code,
        property_type=property_type,
        price_per_m2=payload.price_per_m2,
    )

    if updated_price is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CITY_VALUATION_PRICE_NOT_FOUND",
                "message": (
                    "Não existe preço-base configurado para "
                    "a cidade e tipologia informadas."
                ),
                "city_ibge_code": city_ibge_code,
                "property_type": property_type.value,
            },
        )

    return updated_price
