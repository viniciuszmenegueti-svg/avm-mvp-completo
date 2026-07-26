from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, status

from app.infrastructure.dependencies import DatabaseSession
from app.repositories.cities_sqlalchemy import get_active_city_by_ibge_code
from app.repositories.property_assets_sqlalchemy import (
    create_property_asset as create_property_asset_in_database,
)
from app.repositories.property_assets_sqlalchemy import (
    find_matching_property_asset,
    get_property_asset_by_id,
    list_property_assets as list_property_assets_from_database,
    update_property_asset as update_property_asset_in_database,
)
from app.schemas.property_asset import (
    PropertyAssetCreate,
    PropertyAssetListResponse,
    PropertyAssetResponse,
    PropertyAssetUpdate,
)


router = APIRouter(prefix="/property-assets", tags=["Imóveis"])


@router.post(
    "",
    response_model=PropertyAssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um imóvel",
)
def create_property_asset(
    property_asset: PropertyAssetCreate,
    session: DatabaseSession,
) -> PropertyAssetResponse:
    city = get_active_city_by_ibge_code(
        session=session,
        city_ibge_code=property_asset.city_ibge_code,
    )

    if city is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "UNSUPPORTED_CITY",
                "message": (
                    "A cidade informada não está habilitada para cadastro de imóveis."
                ),
                "city_ibge_code": property_asset.city_ibge_code,
            },
        )

    duplicate = find_matching_property_asset(
        session=session,
        property_asset=property_asset,
    )

    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DUPLICATE_PROPERTY_ASSET",
                "message": (
                    "Já existe um imóvel cadastrado para este endereço e unidade."
                ),
                "property_asset_id": duplicate.property_asset_id,
            },
        )

    return create_property_asset_in_database(
        session=session,
        property_asset_id=str(uuid4()),
        property_asset=property_asset,
    )


@router.get(
    "",
    response_model=PropertyAssetListResponse,
    summary="Lista imóveis",
)
def list_property_assets(
    session: DatabaseSession,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    city_ibge_code: str | None = Query(
        default=None,
        min_length=7,
        max_length=7,
        pattern=r"^\d{7}$",
    ),
) -> PropertyAssetListResponse:
    assets, total = list_property_assets_from_database(
        session=session,
        limit=limit,
        offset=offset,
        city_ibge_code=city_ibge_code,
    )

    return PropertyAssetListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=assets,
    )


@router.get(
    "/{property_asset_id}",
    response_model=PropertyAssetResponse,
    summary="Consulta um imóvel",
)
def get_property_asset(
    property_asset_id: UUID,
    session: DatabaseSession,
) -> PropertyAssetResponse:
    property_asset = get_property_asset_by_id(
        session=session,
        property_asset_id=str(property_asset_id),
    )

    if property_asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PROPERTY_ASSET_NOT_FOUND",
                "message": "Imóvel não encontrado.",
                "property_asset_id": str(property_asset_id),
            },
        )

    return property_asset


@router.patch(
    "/{property_asset_id}",
    response_model=PropertyAssetResponse,
    summary="Atualiza um imóvel",
)
def update_property_asset(
    property_asset_id: UUID,
    update: PropertyAssetUpdate,
    session: DatabaseSession,
) -> PropertyAssetResponse:
    property_asset = update_property_asset_in_database(
        session=session,
        property_asset_id=str(property_asset_id),
        update=update,
    )

    if property_asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PROPERTY_ASSET_NOT_FOUND",
                "message": "Imóvel não encontrado.",
                "property_asset_id": str(property_asset_id),
            },
        )

    return property_asset
