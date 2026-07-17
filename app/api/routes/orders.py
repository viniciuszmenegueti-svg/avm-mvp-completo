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
    UnsupportedCityError,
)
from app.infrastructure.database import SessionLocal
from app.repositories.orders_sqlite import (
    create_order as create_order_in_database,
)
from app.repositories.orders_sqlite import (
    get_order_by_external_id,
    get_order_by_internal_id,
    list_orders as list_orders_from_database,
)
from app.schemas.order import (
    OrderCreate,
    OrderListResponse,
    OrderResponse,
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
def create_order(order: OrderCreate) -> OrderResponse:
    with SessionLocal() as session:
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
            session,
            order.external_order_id,
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

        internal_order_id = str(uuid4())
        received_at = datetime.now(timezone.utc)

        return create_order_in_database(
            session=session,
            order=order,
            internal_order_id=internal_order_id,
            received_at=received_at,
        )


@router.get(
    "",
    response_model=OrderListResponse,
    summary="Lista as Ordens de Serviço",
)
def list_orders(
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
) -> OrderListResponse:
    with SessionLocal() as session:
        orders, total = list_orders_from_database(
            session=session,
            limit=limit,
            offset=offset,
        )

        return OrderListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=orders,
        )


@router.get(
    "/{internal_order_id}",
    response_model=OrderResponse,
    summary="Consulta uma Ordem de Serviço",
)
def get_order(internal_order_id: UUID) -> OrderResponse:
    with SessionLocal() as session:
        order = get_order_by_internal_id(
            session,
            str(internal_order_id),
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
