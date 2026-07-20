from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    status,
)

from app.infrastructure.dependencies import (
    DatabaseSession,
)
from app.repositories.order_status_history_sqlalchemy import (
    list_order_status_history,
)
from app.repositories.orders_sqlalchemy import (
    get_order_by_internal_id,
)
from app.schemas.order_status_history import (
    OrderStatusHistoryResponse,
)


router = APIRouter(
    prefix="/orders",
    tags=["Histórico de Status"],
)


@router.get(
    "/{internal_order_id}/status-history",
    response_model=list[OrderStatusHistoryResponse],
    summary="Consulta o histórico de status da ordem",
)
def get_order_status_history(
    internal_order_id: UUID,
    session: DatabaseSession,
) -> list[OrderStatusHistoryResponse]:
    order_id = str(internal_order_id)

    existing_order = get_order_by_internal_id(
        session=session,
        internal_order_id=order_id,
    )

    if existing_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ORDER_NOT_FOUND",
                "message": ("Ordem de Serviço não encontrada."),
                "internal_order_id": order_id,
            },
        )

    history = list_order_status_history(
        session=session,
        internal_order_id=order_id,
    )

    return [OrderStatusHistoryResponse.model_validate(item) for item in history]
