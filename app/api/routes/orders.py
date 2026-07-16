from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status

from app.infrastructure.database import SessionLocal
from app.repositories.orders_sqlite import (
    create_order as create_order_in_database,
)
from app.repositories.orders_sqlite import (
    get_order_by_external_id,
    get_order_by_internal_id,
)
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
)

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
        existing_order = get_order_by_external_id(
            session,
            order.external_order_id,
        )

        if existing_order is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": (
                        "Já existe uma Ordem de Serviço "
                        "com este external_order_id."
                    ),
                    "external_order_id": (
                        order.external_order_id
                    ),
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
                detail="Ordem de Serviço não encontrada",
            )

        return order
