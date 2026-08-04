from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)

from app.core.client_auth import require_client_api_key
from app.domain.exceptions import (
    InvalidOrderStatusTransitionError,
)
from app.infrastructure.dependencies import DatabaseSession
from app.repositories.orders_sqlalchemy import (
    get_order_by_internal_id,
)
from app.repositories.valuations_sqlalchemy import (
    get_valuation_by_internal_order_id,
)
from app.schemas.order import OrderStatus
from app.schemas.order_processing import OrderProcessResponse
from app.schemas.valuation import ValuationResponse
from app.services.order_processing_service import (
    OrderProcessingStateError,
    process_order,
)
from app.services.valuation_service import (
    calculate_and_store_valuation,
)
from app.services.report_service import build_valuation_csv, build_valuation_pdf
from engine.exceptions import ValuationCalculationError
from engine.registry import ModelVersionNotActiveError


router = APIRouter(
    prefix="/orders",
    dependencies=[Depends(require_client_api_key)],
    tags=["Avaliações AVM"],
)

ClientActor = Annotated[str, Depends(require_client_api_key)]


@router.post(
    "/{internal_order_id}/valuation",
    response_model=ValuationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Calcula e armazena a avaliação AVM de uma ordem",
)
def create_order_valuation(
    internal_order_id: UUID,
    session: DatabaseSession,
    request: Request,
    client_actor: ClientActor,
) -> ValuationResponse:
    order_id = str(internal_order_id)

    try:
        valuation = calculate_and_store_valuation(
            session=session,
            internal_order_id=order_id,
            changed_by=client_actor,
            request_id=str(request.state.request_id),
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
    except ModelVersionNotActiveError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "AVM_MODEL_NOT_ACTIVE",
                "message": str(error),
                "method": error.method.value,
                "model_status": error.model_status.value,
                "internal_order_id": order_id,
            },
        ) from error
    except ValuationCalculationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "VALUATION_CALCULATION_ERROR",
                "message": str(error),
                "internal_order_id": order_id,
            },
        ) from error

    if valuation is None:
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

        if order.status == OrderStatus.REFUSED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "ORDER_REFUSED",
                    "message": ("A Ordem de Serviço foi recusada durante a avaliação."),
                    "internal_order_id": order_id,
                    "refusal_url": f"/orders/{order_id}/refusal",
                },
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "VALUATION_NOT_CREATED",
                "message": "A avaliação AVM não pôde ser criada.",
                "internal_order_id": order_id,
            },
        )

    return valuation


@router.post(
    "/{internal_order_id}/process",
    response_model=OrderProcessResponse,
    summary="Processa uma Ordem de Serviço de forma automática e idempotente",
    responses={
        404: {"description": "Ordem não encontrada"},
        409: {"description": "Estado incompatível com processamento"},
        422: {"description": "Dados incompatíveis com o modelo"},
        503: {"description": "Modelo aplicável indisponível"},
    },
)
def process_order_automatically(
    internal_order_id: UUID,
    session: DatabaseSession,
    request: Request,
    client_actor: ClientActor,
) -> OrderProcessResponse:
    order_id = str(internal_order_id)
    try:
        result = process_order(
            session=session,
            internal_order_id=order_id,
            changed_by=client_actor,
            request_id=str(request.state.request_id),
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
    except OrderProcessingStateError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ORDER_PROCESSING_STATE_INVALID",
                "message": str(error),
                "current_status": error.status.value,
                "internal_order_id": order_id,
            },
        ) from error
    except ModelVersionNotActiveError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "AVM_MODEL_NOT_ACTIVE",
                "message": str(error),
                "method": error.method.value,
                "model_status": error.model_status.value,
                "internal_order_id": order_id,
            },
        ) from error
    except ValuationCalculationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "VALUATION_CALCULATION_ERROR",
                "message": str(error),
                "internal_order_id": order_id,
            },
        ) from error

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ORDER_NOT_FOUND",
                "message": "Ordem de Serviço não encontrada.",
                "internal_order_id": order_id,
            },
        )
    return result


@router.get(
    "/{internal_order_id}/valuation",
    response_model=ValuationResponse,
    summary="Consulta a avaliação AVM de uma ordem",
)
def get_order_valuation(
    internal_order_id: UUID,
    session: DatabaseSession,
) -> ValuationResponse:
    order_id = str(internal_order_id)

    valuation = get_valuation_by_internal_order_id(
        session=session,
        internal_order_id=order_id,
    )

    if valuation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "VALUATION_NOT_FOUND",
                "message": "Avaliação AVM não encontrada.",
                "internal_order_id": order_id,
            },
        )

    return valuation


def _get_order_and_valuation(
    session: DatabaseSession,
    internal_order_id: UUID,
) -> tuple:
    order_id = str(internal_order_id)
    order = get_order_by_internal_id(session=session, internal_order_id=order_id)
    valuation = get_valuation_by_internal_order_id(
        session=session,
        internal_order_id=order_id,
    )
    if order is None or valuation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "VALUATION_NOT_FOUND",
                "message": "Avaliação AVM não encontrada.",
                "internal_order_id": order_id,
            },
        )
    return order, valuation


@router.get(
    "/{internal_order_id}/valuation/report.csv",
    summary="Exporta a precificação em CSV",
)
def export_order_valuation_csv(
    internal_order_id: UUID,
    session: DatabaseSession,
) -> Response:
    order, valuation = _get_order_and_valuation(session, internal_order_id)
    content = build_valuation_csv(order, valuation)
    filename_prefix = (
        "HOMOLOGACAO-" if valuation.execution_mode == "HOMOLOGATION_SHADOW" else ""
    )
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename_prefix}valuation-'
                f'{internal_order_id}.csv"'
            ),
            "X-AVM-Execution-Mode": valuation.execution_mode,
            "X-Contractual-Validity": str(valuation.contractual_validity).lower(),
        },
    )


@router.get(
    "/{internal_order_id}/valuation/report.pdf",
    summary="Exporta o relatório de precificação em PDF",
)
def export_order_valuation_pdf(
    internal_order_id: UUID,
    session: DatabaseSession,
) -> Response:
    order, valuation = _get_order_and_valuation(session, internal_order_id)
    content = build_valuation_pdf(order, valuation)
    filename_prefix = (
        "HOMOLOGACAO-" if valuation.execution_mode == "HOMOLOGATION_SHADOW" else ""
    )
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename_prefix}valuation-'
                f'{internal_order_id}.pdf"'
            ),
            "X-AVM-Execution-Mode": valuation.execution_mode,
            "X-Contractual-Validity": str(valuation.contractual_validity).lower(),
        },
    )
