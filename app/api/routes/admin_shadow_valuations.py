from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.admin_auth import require_admin_api_key
from app.infrastructure.dependencies import DatabaseSession
from app.repositories.orders_sqlalchemy import get_order_by_internal_id
from app.repositories.shadow_valuation_executions_sqlalchemy import (
    summarize_shadow_valuation_executions,
    search_shadow_valuation_executions,
    get_shadow_valuation_execution,
    list_paginated_shadow_valuation_executions_by_order,
)
from app.schemas.shadow_valuation_execution import (
    ShadowValuationExecutionSummaryResponse,
    ShadowValuationExecutionSearchResponse,
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





@router.get(
    "/shadow-valuation-executions",
    response_model=ShadowValuationExecutionSearchResponse,
    summary="Pesquisa execu??es do modelo sombra",
)
def search_shadow_valuation_execution_history(
    session: DatabaseSession,
    actor: AdminActor,
    result_status: str | None = Query(
        default=None,
        description="Status da execu??o sombra.",
    ),
    internal_order_id: str | None = Query(
        default=None,
        description="Identificador interno da Ordem de Servi?o.",
    ),
    requested_by: str | None = Query(
        default=None,
        description="Ator que solicitou a execu??o.",
    ),
    model_version: str | None = Query(
        default=None,
        description="Vers?o do modelo executado.",
    ),
    neighborhood: str | None = Query(
        default=None,
        description="Bairro utilizado na execu??o.",
    ),
    executed_from: datetime | None = Query(
        default=None,
        description="Data inicial da execu??o, inclusive.",
    ),
    executed_until: datetime | None = Query(
        default=None,
        description="Data final da execu??o, inclusive.",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
) -> ShadowValuationExecutionSearchResponse:
    """Pesquisa o hist?rico global de execu??es sombra."""

    if (
        executed_from is not None
        and executed_until is not None
        and executed_from > executed_until
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "INVALID_EXECUTION_PERIOD",
                "message": (
                    "A data inicial n?o pode ser posterior "
                    "? data final."
                ),
            },
        )

    items, total = search_shadow_valuation_executions(
        session=session,
        result_status=result_status,
        internal_order_id=internal_order_id,
        requested_by=requested_by,
        model_version=model_version,
        neighborhood=neighborhood,
        executed_from=executed_from,
        executed_until=executed_until,
        limit=limit,
        offset=offset,
    )

    return ShadowValuationExecutionSearchResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )





@router.get(
    "/shadow-valuation-executions/summary",
    response_model=ShadowValuationExecutionSummaryResponse,
    summary="Resume execu??es do modelo sombra",
)
def summarize_shadow_valuation_execution_history(
    session: DatabaseSession,
    actor: AdminActor,
    executed_from: datetime | None = Query(
        default=None,
        description="Data inicial da execu??o, inclusive.",
    ),
    executed_until: datetime | None = Query(
        default=None,
        description="Data final da execu??o, inclusive.",
    ),
) -> ShadowValuationExecutionSummaryResponse:
    """Retorna indicadores operacionais das execu??es sombra."""

    if (
        executed_from is not None
        and executed_until is not None
        and executed_from > executed_until
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "INVALID_EXECUTION_PERIOD",
                "message": (
                    "A data inicial n?o pode ser posterior "
                    "? data final."
                ),
            },
        )

    summary = summarize_shadow_valuation_executions(
        session=session,
        executed_from=executed_from,
        executed_until=executed_until,
    )

    return ShadowValuationExecutionSummaryResponse(
        **summary
    )


@router.get(
    "/shadow-valuation-executions/{execution_id}",
    response_model=ShadowValuationExecutionResponse,
    summary="Consulta uma execu??o do modelo sombra",
)
def get_shadow_valuation_execution_detail(
    execution_id: str,
    session: DatabaseSession,
    actor: AdminActor,
) -> ShadowValuationExecutionResponse:
    """Retorna uma execu??o sombra audit?vel pelo identificador."""

    execution = get_shadow_valuation_execution(
        session=session,
        execution_id=execution_id,
    )

    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SHADOW_EXECUTION_NOT_FOUND",
                "message": (
                    "A execu??o do modelo sombra n?o foi encontrada."
                ),
            },
        )

    return ShadowValuationExecutionResponse.model_validate(
        execution
    )

