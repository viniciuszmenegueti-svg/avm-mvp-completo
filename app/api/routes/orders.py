from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    status,
)

from app.domain.exceptions import (
    CityDataMismatchError,
    InvalidOrderStatusTransitionError,
    UnsupportedCityError,
)
from app.infrastructure.dependencies import (
    DatabaseSession,
)
from app.repositories.orders_sqlalchemy import (
    create_order as create_order_in_database,
)
from app.repositories.orders_sqlalchemy import (
    get_order_by_external_id,
    get_order_by_internal_id,
    list_orders as list_orders_from_database,
)
from app.schemas.order import (
    OrderCreate,
    OrderFromPropertyAssetCreate,
    OrderListResponse,
    OrderResponse,
    OrderStatus,
    OrderStatusUpdate,
)
from app.services.order_conflict_of_interest_refusal_service import (
    refuse_order_for_conflict_of_interest,
)
from app.services.order_data_inconsistency_refusal_service import (
    refuse_order_for_city_data_mismatch,
)
from app.services.order_status_update import (
    update_order_status_with_history,
)
from app.services.order_validation import validate_order_city


router = APIRouter(
    prefix="/orders",
    tags=["Ordens de Serviço"],
)


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Recebe uma nova Ordem de Serviço",
)
def create_order(
    order: OrderCreate,
    session: DatabaseSession,
) -> OrderResponse:
    existing_order = get_order_by_external_id(
        session=session,
        external_order_id=order.external_order_id,
    )

    if existing_order is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DUPLICATE_EXTERNAL_ORDER_ID",
                "message": (
                    "Já existe uma Ordem de Serviço com este external_order_id."
                ),
                "external_order_id": order.external_order_id,
                "internal_order_id": existing_order.internal_order_id,
            },
        )

    if order.conflict_of_interest.has_conflict:
        internal_order_id = str(uuid4())

        created_order = create_order_in_database(
            session=session,
            order=order,
            internal_order_id=internal_order_id,
            received_at=datetime.now(timezone.utc),
        )

        refused_order = refuse_order_for_conflict_of_interest(
            session=session,
            internal_order_id=internal_order_id,
            order=order,
        )

        if refused_order is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "code": "ORDER_REFUSAL_FAILED",
                    "message": (
                        "A ordem foi criada, mas não foi possível registrar a recusa."
                    ),
                    "internal_order_id": created_order.internal_order_id,
                },
            )

        return refused_order

    try:
        validate_order_city(
            session=session,
            order=order,
        )
    except UnsupportedCityError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "UNSUPPORTED_CITY",
                "message": str(error),
                "city_ibge_code": error.city_ibge_code,
            },
        ) from error
    except CityDataMismatchError as error:
        internal_order_id = str(uuid4())

        created_order = create_order_in_database(
            session=session,
            order=order,
            internal_order_id=internal_order_id,
            received_at=datetime.now(timezone.utc),
        )

        refused_order = refuse_order_for_city_data_mismatch(
            session=session,
            internal_order_id=internal_order_id,
            order=order,
            expected_city=error.expected_city,
            expected_state=error.expected_state,
        )

        if refused_order is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "code": "ORDER_REFUSAL_FAILED",
                    "message": (
                        "A ordem foi criada, mas não foi possível registrar a recusa."
                    ),
                    "internal_order_id": created_order.internal_order_id,
                },
            ) from error

        return refused_order

    return create_order_in_database(
        session=session,
        order=order,
        internal_order_id=str(uuid4()),
        received_at=datetime.now(timezone.utc),
    )


@router.get(
    "",
    response_model=OrderListResponse,
    summary="Lista as Ordens de Serviço",
)
def list_orders(
    session: DatabaseSession,
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Quantidade máxima de resultados",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Quantidade de registros ignorados",
    ),
    order_status: OrderStatus | None = Query(
        default=None,
        description="Filtra as ordens pelo status",
    ),
) -> OrderListResponse:
    orders, total = list_orders_from_database(
        session=session,
        limit=limit,
        offset=offset,
        order_status=order_status,
    )

    return OrderListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=orders,
    )


@router.patch(
    "/{internal_order_id}/status",
    response_model=OrderResponse,
    summary="Atualiza o status de uma Ordem de Serviço",
)
def update_order_status(
    internal_order_id: UUID,
    status_update: OrderStatusUpdate,
    session: DatabaseSession,
) -> OrderResponse:
    order_id = str(internal_order_id)

    try:
        updated_order = update_order_status_with_history(
            session=session,
            internal_order_id=order_id,
            new_status=status_update.status,
        )
    except InvalidOrderStatusTransitionError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "INVALID_STATUS_TRANSITION",
                "message": str(error),
                "current_status": error.current_status,
                "new_status": error.new_status,
            },
        ) from error

    if updated_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ORDER_NOT_FOUND",
                "message": "Ordem de Serviço não encontrada.",
                "internal_order_id": order_id,
            },
        )

    return updated_order


@router.get(
    "/external/{external_order_id}",
    response_model=OrderResponse,
    summary="Consulta uma ordem pelo identificador externo",
)
def get_order_by_external_identifier(
    external_order_id: str,
    session: DatabaseSession,
) -> OrderResponse:
    order = get_order_by_external_id(
        session=session,
        external_order_id=external_order_id,
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ORDER_NOT_FOUND",
                "message": "Ordem de Serviço não encontrada.",
                "external_order_id": external_order_id,
            },
        )

    return order


@router.get(
    "/{internal_order_id}",
    response_model=OrderResponse,
    summary="Consulta uma Ordem de Serviço",
)
def get_order(
    internal_order_id: UUID,
    session: DatabaseSession,
) -> OrderResponse:
    order = get_order_by_internal_id(
        session=session,
        internal_order_id=str(internal_order_id),
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ORDER_NOT_FOUND",
                "message": "Ordem de Serviço não encontrada.",
                "internal_order_id": str(internal_order_id),
            },
        )

    return order


@router.post(
    "/from-property-asset",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma ordem a partir de um imóvel cadastrado",
)
def create_order_from_property_asset(
    request: OrderFromPropertyAssetCreate,
    session: DatabaseSession,
) -> OrderResponse:
    from app.repositories.cities_sqlalchemy import get_active_city_by_ibge_code
    from app.repositories.property_assets_sqlalchemy import (
        get_property_asset_by_id,
    )
    from app.schemas.property import PropertyInput, PropertyType

    existing_order = get_order_by_external_id(
        session=session,
        external_order_id=request.external_order_id,
    )

    if existing_order is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DUPLICATE_EXTERNAL_ORDER_ID",
                "message": (
                    "Já existe uma Ordem de Serviço com este external_order_id."
                ),
                "external_order_id": request.external_order_id,
                "internal_order_id": existing_order.internal_order_id,
            },
        )

    asset = get_property_asset_by_id(
        session=session,
        property_asset_id=request.property_asset_id,
    )

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PROPERTY_ASSET_NOT_FOUND",
                "message": "Imóvel não encontrado.",
                "property_asset_id": request.property_asset_id,
            },
        )

    city = get_active_city_by_ibge_code(
        session=session,
        city_ibge_code=asset.city_ibge_code,
    )

    if city is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "UNSUPPORTED_CITY",
            },
        )

    property_input = PropertyInput(
        property_type=PropertyType(asset.property_type),
        state=city.state,
        city=city.name,
        city_ibge_code=asset.city_ibge_code,
        postal_code=asset.postal_code,
        neighborhood=asset.neighborhood,
        street=asset.street,
        number=asset.number,
        complement=asset.complement,
        private_area_m2=(
            float(asset.private_area_m2) if asset.private_area_m2 is not None else None
        ),
        built_area_m2=(
            float(asset.built_area_m2) if asset.built_area_m2 is not None else None
        ),
        land_area_m2=(
            float(asset.land_area_m2) if asset.land_area_m2 is not None else None
        ),
        bedrooms=asset.bedrooms,
        bathrooms=asset.bathrooms,
        parking_spaces=asset.parking_spaces,
    )

    order = OrderCreate(
        external_order_id=request.external_order_id,
        property=property_input,
    )

    return create_order_in_database(
        session=session,
        order=order,
        internal_order_id=str(uuid4()),
        received_at=datetime.now(timezone.utc),
        property_asset_id=asset.property_asset_id,
    )
