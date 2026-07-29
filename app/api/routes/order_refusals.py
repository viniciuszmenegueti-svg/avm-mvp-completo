from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.core.client_auth import require_client_api_key
from app.infrastructure.dependencies import DatabaseSession
from app.repositories.order_refusals_sqlalchemy import (
    get_order_refusal_by_internal_order_id,
)
from app.repositories.orders_sqlalchemy import (
    get_order_by_internal_id,
)
from app.schemas.order_refusal import OrderRefusalResponse


router = APIRouter(
    prefix="/orders",
    dependencies=[Depends(require_client_api_key)],
    tags=["Recusas de Ordens"],
)


@router.get(
    "/{internal_order_id}/refusal",
    response_model=OrderRefusalResponse,
    summary="Consulta o motivo de recusa de uma Ordem de Serviço",
)
def get_order_refusal(
    internal_order_id: UUID,
    session: DatabaseSession,
) -> OrderRefusalResponse:
    order_id = str(internal_order_id)

    order = get_order_by_internal_id(
        session=session,
        internal_order_id=order_id,
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ORDER_NOT_FOUND",
                "message": "Ordem de Serviço não encontrada.",
                "internal_order_id": order_id,
            },
        )

    refusal = get_order_refusal_by_internal_order_id(
        session=session,
        internal_order_id=order_id,
    )

    if refusal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ORDER_REFUSAL_NOT_FOUND",
                "message": "A ordem não possui recusa registrada.",
                "internal_order_id": order_id,
            },
        )

    return OrderRefusalResponse.model_validate(refusal)
