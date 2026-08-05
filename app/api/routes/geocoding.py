from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.client_auth import require_client_api_key
from app.infrastructure.dependencies import DatabaseSession
from app.repositories.cities_sqlalchemy import get_active_city_by_ibge_code
from app.schemas.geocoding import GeocodingAddressRequest, GeocodingResponse
from app.services.geocoding_service import normalize_text, resolve_cnefe_address


ClientActor = Annotated[str, Depends(require_client_api_key)]

router = APIRouter(prefix="/geocoding", tags=["Geolocalização"])


@router.post(
    "/resolve",
    response_model=GeocodingResponse,
    summary="Resolve endereço na base local auditável do CNEFE/IBGE",
)
def resolve_address(
    payload: GeocodingAddressRequest,
    session: DatabaseSession,
    requested_by: ClientActor,
) -> GeocodingResponse:
    city = get_active_city_by_ibge_code(session, payload.city_ibge_code)
    if city is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "UNSUPPORTED_CITY",
                "message": "A cidade informada não está ativa para avaliação.",
            },
        )
    if city.state != payload.state or normalize_text(city.name) != normalize_text(
        payload.city
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "CITY_DATA_MISMATCH",
                "message": "Cidade, UF e código IBGE não correspondem.",
                "expected_city": city.name,
                "expected_state": city.state,
            },
        )
    return resolve_cnefe_address(
        session,
        payload=payload,
        requested_by=requested_by,
    )
