from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.domain.exceptions import (
    CityDataMismatchError,
    InvalidOrderStatusTransitionError,
    UnsupportedCityError,
)
from app.infrastructure.dependencies import (
    get_database_session,
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
    OrderListResponse,
    OrderResponse,
    OrderStatus,
    OrderStatusUpdate,
)
from app.services.order_status_update import (
    update_order_status_with_history,
)
from app.services.order_validation import validate_order_city


router = APIRouter(
    prefix="/orders",
    tags=["Ordens de Serviço"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


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
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "CITY_DATA_MISMATCH",
                "message": str(error),
                "city_ibge_code": error.city_ibge_code,
                "expected_city": error.expected_city,
                "expected_state": error.expected_state,
            },
        ) from error

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
                    "Já existe uma Ordem de Serviço "
                    "com este external_order_id."
                ),
                "external_order_id": order.external_order_id,
                "internal_order_id": (
                    existing_order.internal_order_id
                ),
            },
        )

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
                "message": (
                    "Ordem de Serviço não encontrada."
                ),
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
                "message": (
                    "Ordem de Serviço não encontrada."
                ),
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
                "message": (
                    "Ordem de Serviço não encontrada."
                ),
                "internal_order_id": str(internal_order_id),
            },
        )

    return order
