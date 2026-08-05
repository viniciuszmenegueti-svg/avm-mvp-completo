from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.admin_auth import require_admin_api_key
from app.infrastructure.dependencies import DatabaseSession
from app.repositories.orders_sqlalchemy import get_order_by_internal_id
from app.repositories.shadow_valuation_executions_sqlalchemy import (
    list_paginated_shadow_valuation_executions_by_order,
)
from app.schemas.shadow_valuation_execution import (
    ShadowValuationExecutionListResponse,
    ShadowValuationExecutionResponse,
)


router = APIRouter(prefix="/admin", tags=["Administração"])
AdminActor = Annotated[str, Depends(require_admin_api_key)]


@router.get(
    "/orders/{internal_order_id}/shadow-valuation-executions",
    response_model=ShadowValuationExecutionListResponse,
    summary="Consulta o histórico de execuções do modelo sombra",
)
def list_order_shadow_valuation_executions(
    internal_order_id: UUID,
    session: DatabaseSession,
    _actor: AdminActor,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ShadowValuationExecutionListResponse:
    """Lista a auditoria sombra sem expor ou alterar a avaliação oficial."""

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
                "message": "Ordem de Serviço não encontrada.",
                "internal_order_id": order_id,
            },
        )

    executions, total = list_paginated_shadow_valuation_executions_by_order(
        session=session,
        internal_order_id=order_id,
        limit=limit,
        offset=offset,
    )

    return ShadowValuationExecutionListResponse(
        internal_order_id=order_id,
        total=total,
        limit=limit,
        offset=offset,
        items=[
            ShadowValuationExecutionResponse.model_validate(execution)
            for execution in executions
        ],
    )
